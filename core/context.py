import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple

from core.config import get_async_openai_client, get_default_distill_model, load_config
from core.storage import (
    calculate_active_tokens,
    commit_distillation,
    estimate_tokens,
    get_session,
)

DISTILLER_SYSTEM_PROMPT = (
    "Ты — специализированный ИИ-дистиллятор контекста и архитектор рабочей памяти автономного агента. "
    "Твоя цель — объединить предыдущую рабочую память (если есть) и новые шаги диалога (команды, файлы, выводы терминала) "
    "в СУХУЮ, ТОЧНУЮ КВИНТЭССЕНЦИЮ. Никаких приветствий и воды.\n\n"
    "Сформируй обновлённую рабочую память строго по блокам:\n"
    "### 🎯 Целевая задача пользователя:\n"
    "Кратко и точно суть решаемой задачи.\n\n"
    "### 📌 Подтверждённые факты и окружение:\n"
    "Точные пути к файлам, IP, порты, эндпоинты, версии, уже внесённые изменения.\n\n"
    "### ❌ Что проверено и НЕ сработало:\n"
    "Ошибки, нерабочие команды и тупиковые гипотезы (чтобы агент их не повторял).\n\n"
    "### ⏳ Текущий статус и следующий шаг:\n"
    "На чём остановились и что конкретно нужно сделать дальше."
)

session_distill_status: Dict[str, dict] = {}
_distill_locks: Dict[str, asyncio.Lock] = {}


def get_distill_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _distill_locks:
        _distill_locks[session_id] = asyncio.Lock()
    return _distill_locks[session_id]


def _normalize_tool_calls(raw_tcs: list) -> List[dict]:
    norm = []
    for idx, tc in enumerate(raw_tcs):
        if not isinstance(tc, dict):
            continue
        tc_id = tc.get("id") or f"call_migrated_{idx}"
        fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
        norm.append(
            {
                "id": tc_id,
                "type": "function",
                "function": {
                    "name": fn.get("name") or "bash",
                    "arguments": fn.get("arguments") if isinstance(fn.get("arguments"), str) else json.dumps(fn.get("arguments") or {}),
                },
            }
        )
    return norm


def _group_atomic_units(raw_messages: List[dict]) -> List[Tuple[List[dict], List[dict]]]:
    """
    Returns list of (api_unit, orig_unit) tuples where each api_unit is an indivisible
    valid sequence of OpenAI chat messages and orig_unit contains matching original session entries.
    Automatically repairs broken tool_call sequences and drops orphan tool messages.
    """
    units: List[Tuple[List[dict], List[dict]]] = []
    n = len(raw_messages)
    i = 0

    while i < n:
        m = raw_messages[i]
        role = m.get("role")

        if role == "user":
            content = str(m.get("content") or "")
            units.append(([{"role": "user", "content": content}], [m]))
            i += 1
            continue

        if role == "tool":
            # Orphan tool output without preceding assistant.tool_calls -> skip safely
            i += 1
            continue

        if role == "assistant":
            raw_tcs = m.get("tool_calls")
            if raw_tcs and isinstance(raw_tcs, list):
                norm_tcs = _normalize_tool_calls(raw_tcs)
                if not norm_tcs:
                    content = m.get("content")
                    if content:
                        units.append(([{"role": "assistant", "content": str(content)}], [m]))
                    i += 1
                    continue

                expected_ids = [tc["id"] for tc in norm_tcs]
                expected_set = set(expected_ids)
                asst_msg: dict = {
                    "role": "assistant",
                    "content": m.get("content") or None,
                    "tool_calls": norm_tcs,
                }

                collected_by_id: Dict[str, str] = {}
                orig_group = [m]
                j = i + 1
                while j < n and raw_messages[j].get("role") == "tool":
                    tm = raw_messages[j]
                    orig_group.append(tm)
                    tc_id = tm.get("tool_call_id")
                    if tc_id in expected_set and tc_id not in collected_by_id:
                        collected_by_id[tc_id] = str(tm.get("content") or "")
                    j += 1

                api_group = [asst_msg]
                for tc_id in expected_ids:
                    tool_content = collected_by_id.get(tc_id, "[Выполнение было прервано]")
                    api_group.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": tool_content,
                        }
                    )

                units.append((api_group, orig_group))
                i = j
                continue

            content = m.get("content")
            if content:
                units.append(([{"role": "assistant", "content": str(content)}], [m]))
            i += 1
            continue

        i += 1

    return units


def _msg_tokens(msg: dict) -> int:
    total = estimate_tokens(msg.get("content") or "")
    if msg.get("tool_calls"):
        total += estimate_tokens(json.dumps(msg["tool_calls"], ensure_ascii=False))
    return total + 4


def _unit_tokens(api_unit: List[dict]) -> int:
    return sum(_msg_tokens(m) for m in api_unit)


def _shrink_unit_to_budget(api_unit: List[dict], max_tokens: int) -> List[dict]:
    cloned = [dict(m) for m in api_unit]
    if _unit_tokens(cloned) <= max_tokens:
        return cloned

    marker = "\n...[обрезано по лимиту контекста]...\n"
    marker_toks = estimate_tokens(marker)

    # First shrink long tool/message contents iteratively until total tokens <= max_tokens
    for pass_limit in (max(80, max_tokens // max(1, len(cloned))), 40, 0):
        if _unit_tokens(cloned) <= max_tokens:
            break
        for m in cloned:
            if _unit_tokens(cloned) <= max_tokens:
                break
            content = m.get("content")
            if not isinstance(content, str) or len(content) <= 120:
                continue
            cur_unit_toks = _unit_tokens(cloned)
            excess_toks = cur_unit_toks - max_tokens
            m_toks = estimate_tokens(content)
            target_m_toks = max(pass_limit, m_toks - excess_toks - marker_toks - 8)
            if target_m_toks >= m_toks:
                continue
            if target_m_toks <= 20:
                m["content"] = "[содержимое обрезано по лимиту контекста]"
            else:
                ratio = target_m_toks / max(1, m_toks)
                keep_chars = max(40, int(len(content) * ratio * 0.85))
                half = keep_chars // 2
                m["content"] = content[:half] + marker + content[-half:]
                # Fine-tune if Unicode/ASCII mix overshoots slightly
                while _unit_tokens(cloned) > max_tokens and half > 20:
                    half = int(half * 0.7)
                    m["content"] = content[:half] + marker + content[-half:]

    return cloned


def build_safe_api_messages(
    session: dict,
    system_content: str,
    context_limit: int,
) -> List[dict]:
    sys_msg = {"role": "system", "content": system_content}
    sys_tokens = _msg_tokens(sys_msg)

    raw_working = [
        m
        for m in session.get("messages", [])
        if not m.get("compressed")
        and not m.get("is_distilled_memory")
        and not m.get("is_distilled_ack")
        and m.get("role") in ("user", "assistant", "tool")
    ]

    units = [api_u for api_u, _ in _group_atomic_units(raw_working)]
    if not units:
        return [sys_msg]

    total_unit_tokens = sum(_unit_tokens(u) for u in units)
    if sys_tokens + total_unit_tokens <= context_limit:
        out = [sys_msg]
        for u in units:
            out.extend(u)
        return out

    # Need sliding window over indivisible TurnUnits
    has_active_memory = bool((session.get("active_memory") or "").strip())
    first_user_unit = next((u for u in units if u[0].get("role") == "user"), None)

    available_budget = max(512, context_limit - sys_tokens)
    preserve_first: Optional[List[dict]] = None
    if not has_active_memory and first_user_unit and first_user_unit is not units[-1]:
        fu_tokens = _unit_tokens(first_user_unit)
        if fu_tokens <= int(available_budget * 0.25):
            preserve_first = first_user_unit
            available_budget -= fu_tokens

    kept_reversed: List[List[dict]] = []
    remaining = available_budget

    for idx in range(len(units) - 1, -1, -1):
        u = units[idx]
        if preserve_first is not None and u is preserve_first:
            continue
        u_toks = _unit_tokens(u)
        if u_toks <= remaining:
            kept_reversed.append(u)
            remaining -= u_toks
        else:
            if not kept_reversed:
                kept_reversed.append(_shrink_unit_to_budget(u, remaining))
            break

    kept_reversed.reverse()

    final_messages = [sys_msg]
    if preserve_first is not None and (not kept_reversed or kept_reversed[0] is not preserve_first):
        final_messages.extend(preserve_first)
    for u in kept_reversed:
        final_messages.extend(u)
    return final_messages


def _format_history_for_distiller(messages: List[dict], existing_memory: str) -> str:
    blocks: List[str] = []
    if existing_memory.strip():
        blocks.append(f"🧠 [ПРЕДЫДУЩАЯ РАБОЧАЯ ПАМЯТЬ (дополнить и актуализировать)]:\n{existing_memory.strip()}")

    for m in messages:
        r = m.get("role")
        if r == "user":
            blocks.append(f"👤 [Пользователь]: {m.get('content') or ''}")
        elif r == "assistant":
            txt = (m.get("content") or "").strip()
            if m.get("tool_calls"):
                calls = []
                for tc in m["tool_calls"]:
                    fn = tc.get("function", {})
                    fname = fn.get("name", "bash")
                    raw_args = fn.get("arguments", "")
                    calls.append(f"{fname}({raw_args[:240]})")
                blocks.append("🤖 [Ассистент вызвал инструменты]:\n" + "\n".join(calls))
            if txt:
                blocks.append(f"🤖 [Ассистент]:\n{txt[:600]}")
        elif r == "tool":
            name = m.get("tool_name") or m.get("command") or "tool"
            out = (m.get("content") or "")[:500]
            blocks.append(f"💻 [Результат '{name}']:\n{out}")

    text = "\n\n".join(blocks)
    if len(text) > 48000:
        text = "[...более ранние детали усечены...]\n\n" + text[-48000:]
    return text


async def distill_session_async(session_id: str, fallback_model: Optional[str] = None) -> None:
    lock = get_distill_lock(session_id)
    if lock.locked():
        return

    async with lock:
        session = await get_session(session_id)
        if not session:
            return

        working = [
            m
            for m in session.get("messages", [])
            if not m.get("compressed")
            and not m.get("is_distilled_memory")
            and not m.get("is_distilled_ack")
            and m.get("role") in ("user", "assistant", "tool")
        ]

        units = _group_atomic_units(working)
        if len(units) < 3:
            session_distill_status[session_id] = {
                "status": "skipped",
                "message": "Слишком мало новых сообщений для сжатия",
            }
            return

        # Keep the last user turn (and any subsequent tool steps) uncompressed;
        # if there is only one user turn with many tool steps, keep at least the last 2 atomic units.
        user_unit_indices = [idx for idx, (api_u, _) in enumerate(units) if api_u[0].get("role") == "user"]
        if len(user_unit_indices) > 1:
            split_unit_idx = user_unit_indices[-1]
        elif len(units) > 3:
            split_unit_idx = len(units) - 2
        else:
            session_distill_status[session_id] = {
                "status": "skipped",
                "message": "Нечего сжимать — текущий шаг ещё активен",
            }
            return

        if split_unit_idx <= 0:
            return

        to_compress_orig: List[dict] = []
        for _, orig_u in units[:split_unit_idx]:
            to_compress_orig.extend(orig_u)

        compressed_ids = {m["msg_id"] for m in to_compress_orig if m.get("msg_id")}
        if not compressed_ids:
            return

        tokens_before = calculate_active_tokens(session)
        session_distill_status[session_id] = {
            "status": "running",
            "tokens_before": tokens_before,
            "turns_count": len(to_compress_orig),
            "started_at": int(time.time()),
            "partial_text": "",
        }

        existing_memory = session.get("active_memory") or ""
        history_text = _format_history_for_distiller(to_compress_orig, existing_memory)
        user_prompt = (
            f"Ниже рабочая история сессии:\n\n{history_text}\n\n"
            "Сформируй обновлённую, максимально компактную и точную 'Рабочую память' (Active Memory) строго по 4 разделам."
        )

        try:
            cfg = load_config()
            cli = get_async_openai_client()
            primary_model = get_default_distill_model(cfg["provider"])

            async def _stream_with_model(model_name: str) -> str:
                acc = ""
                stream = await cli.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": DISTILLER_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=True,
                    max_tokens=2000,
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        acc += delta
                        if session_id in session_distill_status:
                            session_distill_status[session_id]["partial_text"] = acc
                return acc

            try:
                full_distillation = await _stream_with_model(primary_model)
            except Exception as first_err:
                if fallback_model and fallback_model != primary_model:
                    full_distillation = await _stream_with_model(fallback_model)
                else:
                    raise first_err

            if not full_distillation.strip():
                session_distill_status[session_id] = {
                    "status": "error",
                    "error": "Дистиллятор вернул пустой ответ",
                }
                return

            committed = await commit_distillation(
                session_id=session_id,
                compressed_ids=compressed_ids,
                new_memory=full_distillation.strip(),
                tokens_before=tokens_before,
            )
            if not committed:
                session_distill_status[session_id] = {
                    "status": "error",
                    "error": "Сессия была удалена до завершения дистилляции",
                }
                return

            session_distill_status[session_id] = {
                "status": "done",
                "summary": committed["summary"],
                "tokens_before": committed["tokens_before"],
                "tokens_after": committed["tokens_after"],
                "saved_tokens": committed["saved_tokens"],
                "saved_percent": committed["saved_percent"],
                "finished_at": int(time.time()),
            }
        except Exception as e:
            print(f"[NanoAgent] Ошибка фоновой дистилляции ({session_id}): {e}")
            session_distill_status[session_id] = {
                "status": "error",
                "error": str(e),
            }

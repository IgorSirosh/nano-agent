import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional

from core.config import build_full_system_prompt, fetch_balance_async, get_async_openai_client
from core.context import (
    build_safe_api_messages,
    distill_session_async,
    session_distill_status,
)
from core.key_pool import is_quota_or_balance_error, key_pool
from core.storage import (
    append_session_message,
    calculate_active_tokens,
    get_session,
    update_session_fields,
    update_session_stats,
)
from core.tools import (
    ALL_TOOLS,
    MUTATING_TOOL_NAMES,
    READ_ONLY_TOOLS,
    execute_tool,
    is_execution_approved,
)

active_cancel_events: Dict[str, asyncio.Event] = {}
total_tokens_used_global = 0


def stop_session_execution(session_id: str) -> bool:
    ev = active_cancel_events.get(session_id)
    if ev:
        ev.set()
        return True
    return False


def _format_tool_preview(tool_name: str, args: Dict[str, Any]) -> str:
    if tool_name == "bash":
        return str(args.get("command") or "")
    if tool_name in ("read_file", "write_file", "edit_file"):
        p = str(args.get("path") or "")
        if tool_name == "read_file" and (args.get("start_line") or args.get("end_line")):
            return f"{p} ({args.get('start_line', 1)}..{args.get('end_line', 250)})"
        return p
    if tool_name == "list_dir":
        return str(args.get("path") or ".")
    if tool_name == "search_files":
        pat = str(args.get("pattern") or "")
        pth = str(args.get("path") or ".")
        return f"'{pat}' in {pth}"
    return json.dumps(args, ensure_ascii=False)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def chat_stream_generator(
    session_id: str,
    user_text: str,
    model: str,
    reasoning_effort: str,
    context_limit: int,
    compress_threshold: float,
    mode: str,
    approve_execution: bool,
) -> AsyncGenerator[str, None]:
    global total_tokens_used_global

    cancel_event = asyncio.Event()
    active_cancel_events[session_id] = cancel_event
    cli = None

    try:
        session = await get_session(session_id)
        if not session:
            yield _sse({"type": "error", "error": "Сессия не найдена"})
            yield _sse({"type": "done"})
            return

        current_cwd = session["cwd"]
        active_mode = mode if mode in ("plan", "act") else session["mode"]
        execution_allowed = True if active_mode == "act" else is_execution_approved(user_text, approve_execution)
        tools_schema = ALL_TOOLS if execution_allowed else READ_ONLY_TOOLS

        current_ctx_tokens = calculate_active_tokens(session)
        yield _sse(
            {
                "type": "session_init",
                "session_id": session_id,
                "title": session["title"],
                "cwd": current_cwd,
                "mode": active_mode,
                "execution_allowed": execution_allowed,
                "context_tokens": current_ctx_tokens,
                "context_limit": context_limit,
            }
        )
        await asyncio.sleep(0.01)

        threshold_tokens = int(context_limit * compress_threshold)
        if current_ctx_tokens >= threshold_tokens and len(session["messages"]) >= 4:
            st = session_distill_status.get(session_id, {})
            if st.get("status") != "running":
                asyncio.create_task(distill_session_async(session_id, fallback_model=model, manual=False))
                yield _sse({"type": "distill_started"})
                yield _sse({"type": "status", "text": "Фоновый компрессор памяти запущен..."})

        cli = get_async_openai_client()
        max_iterations = 25
        iteration = 0
        used_mutating_tool = False
        produced_final_text = False
        hit_error = False

        while iteration < max_iterations:
            if cancel_event.is_set():
                yield _sse({"type": "cancelled", "text": "Выполнение остановлено пользователем"})
                break

            iteration += 1
            session = await get_session(session_id)
            if not session:
                break
            current_cwd = session["cwd"]

            system_content = build_full_system_prompt(
                cwd=current_cwd,
                mode=active_mode,
                execution_allowed=execution_allowed,
                active_memory=session.get("active_memory"),
            )
            safe_api_messages = build_safe_api_messages(session, system_content, context_limit)

            extra_params: Dict[str, Any] = {}
            if reasoning_effort in ("low", "medium", "high", "max") and any(
                x in model for x in ("deepseek-r1", "o1", "o3", "o4", "abliterated")
            ):
                extra_params["reasoning_effort"] = reasoning_effort

            yield _sse({"type": "status", "text": "Отправляю запрос к модели..."})

            full_content = ""
            full_reasoning = ""
            tools_map: Dict[int, dict] = {}
            last_usage = None

            try:
                stream = await cli.chat.completions.create(
                    model=model,
                    messages=safe_api_messages,
                    tools=tools_schema,
                    tool_choice="auto",
                    stream=True,
                    stream_options={"include_usage": True},
                    **extra_params,
                )

                async for chunk in stream:
                    if cancel_event.is_set():
                        break
                    if getattr(chunk, "usage", None):
                        last_usage = chunk.usage
                    if not getattr(chunk, "choices", None):
                        continue

                    delta = chunk.choices[0].delta
                    reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                    if reasoning:
                        full_reasoning += reasoning
                        yield _sse({"type": "reasoning", "delta": reasoning})

                    if getattr(delta, "content", None):
                        full_content += delta.content
                        yield _sse({"type": "content", "delta": delta.content})

                    if getattr(delta, "tool_calls", None):
                        for tc in delta.tool_calls:
                            idx = tc.index if tc.index is not None else 0
                            if idx not in tools_map:
                                tools_map[idx] = {
                                    "id": tc.id or f"call_{iteration}_{idx}",
                                    "name": (tc.function.name if tc.function else "") or "",
                                    "arguments": "",
                                }
                            if tc.id:
                                tools_map[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tools_map[idx]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tools_map[idx]["arguments"] += tc.function.arguments
            except Exception as e:
                if is_quota_or_balance_error(e) and key_pool.auto_rotate:
                    yield _sse({"type": "status", "text": "Баланс активного API-ключа исчерпан ($0.00). Выполняется ротация ключа..."})
                    new_pair = await key_pool.rotate_to_next_active(reason=str(e))
                    if new_pair:
                        yield _sse({
                            "type": "key_rotated",
                            "new_key_id": new_pair.id,
                            "label": new_pair.label,
                            "balance": new_pair.formatted_balance,
                        })
                        yield _sse({"type": "status", "text": f"Переключено на {new_pair.label} ({new_pair.formatted_balance}). Повтор запроса..."})
                        cli = get_async_openai_client()
                        continue
                    else:
                        hit_error = True
                        yield _sse({"type": "error", "error": "Все доступные API-ключи исчерпаны ($0.00). Добавьте новый рабочий ключ в настройках."})
                        break
                hit_error = True
                yield _sse({"type": "error", "error": str(e)})
                break

            if cancel_event.is_set():
                if full_content or full_reasoning:
                    await append_session_message(
                        session_id,
                        {
                            "role": "assistant",
                            "content": (full_content + "\n\n*[Остановлено пользователем]*").strip(),
                            "reasoning": full_reasoning or None,
                        },
                    )
                yield _sse({"type": "cancelled", "text": "Генерация остановлена пользователем"})
                break

            if last_usage:
                p_toks = int(getattr(last_usage, "prompt_tokens", 0) or 0)
                c_toks = int(getattr(last_usage, "completion_tokens", 0) or 0)
                t_toks = int(getattr(last_usage, "total_tokens", 0) or (p_toks + c_toks))
                total_tokens_used_global += t_toks
                await update_session_stats(session_id, p_toks, c_toks, t_toks)
                balance = await fetch_balance_async()
                latest_for_count = await get_session(session_id) or session
                ctx_toks = calculate_active_tokens(latest_for_count)
                yield _sse(
                    {
                        "type": "usage",
                        "prompt": p_toks,
                        "completion": c_toks,
                        "total": t_toks,
                        "grand_total": total_tokens_used_global,
                        "balance": balance,
                        "context_tokens": ctx_toks,
                        "context_limit": context_limit,
                    }
                )

            if tools_map:
                tool_calls_list = [
                    {
                        "id": v["id"] or f"call_{iteration}_{i}",
                        "type": "function",
                        "function": {
                            "name": v["name"] or "bash",
                            "arguments": v["arguments"] or "{}",
                        },
                    }
                    for i, v in sorted(tools_map.items())
                ]

                await append_session_message(
                    session_id,
                    {
                        "role": "assistant",
                        "content": full_content or None,
                        "reasoning": full_reasoning or None,
                        "tool_calls": tool_calls_list,
                    },
                )

                for tc in tool_calls_list:
                    fn_name = tc["function"]["name"]
                    args_raw = tc["function"]["arguments"]
                    parse_error: Optional[str] = None
                    try:
                        parsed_args = json.loads(args_raw) if args_raw.strip() else {}
                        if not isinstance(parsed_args, dict):
                            parsed_args = {"command": str(parsed_args)}
                    except Exception as je:
                        if fn_name == "bash":
                            parsed_args = {"command": args_raw}
                        else:
                            parsed_args = {}
                            parse_error = f"[ошибка: невалидный JSON аргументов для {fn_name}: {je}]"

                    preview = _format_tool_preview(fn_name, parsed_args)

                    if cancel_event.is_set():
                        await append_session_message(
                            session_id,
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "tool_name": fn_name,
                                "command": preview,
                                "content": "[выполнение остановлено пользователем]",
                                "exit_code": -1,
                            },
                        )
                        continue

                    yield _sse(
                        {
                            "type": "tool_start",
                            "tool": fn_name,
                            "command": preview,
                            "args": parsed_args,
                        }
                    )

                    if parse_error:
                        tool_res = {"output": parse_error, "exit_code": 1}
                    else:
                        tool_res = await execute_tool(
                            fn_name,
                            parsed_args,
                            current_cwd,
                            cancel_event=cancel_event,
                            allow_mutating=execution_allowed,
                        )

                    if fn_name in MUTATING_TOOL_NAMES and execution_allowed and tool_res.get("exit_code") != -1:
                        used_mutating_tool = True

                    if tool_res.get("new_cwd"):
                        try:
                            await update_session_fields(session_id, cwd=tool_res["new_cwd"])
                            current_cwd = tool_res["new_cwd"]
                        except Exception:
                            pass

                    yield _sse(
                        {
                            "type": "tool_done",
                            "tool": fn_name,
                            "command": preview,
                            "output": tool_res.get("output", ""),
                            "diff": tool_res.get("diff"),
                            "exit_code": tool_res.get("exit_code"),
                            "cwd": current_cwd,
                        }
                    )

                    await append_session_message(
                        session_id,
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "tool_name": fn_name,
                            "command": preview,
                            "diff": tool_res.get("diff"),
                            "exit_code": tool_res.get("exit_code"),
                            "content": tool_res.get("output", ""),
                        },
                    )

                if cancel_event.is_set():
                    yield _sse({"type": "cancelled", "text": "Выполнение остановлено пользователем"})
                    break

                latest_session = await get_session(session_id)
                if latest_session:
                    loop_ctx_tokens = calculate_active_tokens(latest_session)
                    yield _sse(
                        {
                            "type": "context_update",
                            "context_tokens": loop_ctx_tokens,
                            "context_limit": context_limit,
                        }
                    )
                    if loop_ctx_tokens >= threshold_tokens and len(latest_session["messages"]) >= 6:
                        st = session_distill_status.get(session_id, {})
                        if st.get("status") != "running":
                            asyncio.create_task(distill_session_async(session_id, fallback_model=model, manual=False))
                            yield _sse({"type": "distill_started"})
                            yield _sse({"type": "status", "text": "Фоновый компрессор памяти запущен..."})

                continue

            if full_content or full_reasoning:
                produced_final_text = True
                await append_session_message(
                    session_id,
                    {
                        "role": "assistant",
                        "content": full_content,
                        "reasoning": full_reasoning or None,
                    },
                )
            break

        # Reached max iterations while ending on a tool response -> summarize safely
        if not cancel_event.is_set() and not hit_error and iteration >= max_iterations:
            latest_session = await get_session(session_id)
            if latest_session and latest_session["messages"] and latest_session["messages"][-1].get("role") == "tool":
                yield _sse({"type": "status", "text": "Достигнут лимит шагов (25). Подвожу итог..."})
                try:
                    sys_content = build_full_system_prompt(
                        cwd=latest_session["cwd"],
                        mode=active_mode,
                        execution_allowed=execution_allowed,
                        active_memory=latest_session.get("active_memory"),
                    )
                    safe_final_msgs = build_safe_api_messages(latest_session, sys_content, context_limit)
                    extra_params: Dict[str, Any] = {}
                    if reasoning_effort in ("low", "medium", "high", "max") and any(
                        x in model for x in ("deepseek-r1", "o1", "o3", "o4", "abliterated")
                    ):
                        extra_params["reasoning_effort"] = reasoning_effort

                    final_stream = await cli.chat.completions.create(
                        model=model,
                        messages=safe_final_msgs,
                        tool_choice="none",
                        stream=True,
                        **extra_params,
                    )
                    final_content = ""
                    final_reasoning = ""
                    async for chunk in final_stream:
                        if cancel_event.is_set():
                            break
                        if not getattr(chunk, "choices", None):
                            continue
                        delta = chunk.choices[0].delta
                        reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                        if reasoning:
                            final_reasoning += reasoning
                            yield _sse({"type": "reasoning", "delta": reasoning})
                        if getattr(delta, "content", None):
                            final_content += delta.content
                            yield _sse({"type": "content", "delta": delta.content})

                    if final_content:
                        produced_final_text = True
                        await append_session_message(
                            session_id,
                            {
                                "role": "assistant",
                                "content": final_content,
                                "reasoning": final_reasoning or None,
                            },
                        )
                except Exception as e:
                    err_msg = f"\n[Достигнут лимит шагов; ошибка финализации: {e}]"
                    await append_session_message(session_id, {"role": "assistant", "content": err_msg})
                    yield _sse({"type": "content", "delta": err_msg})

        if (
            active_mode == "plan"
            and not execution_allowed
            and not used_mutating_tool
            and produced_final_text
            and not cancel_event.is_set()
            and not hit_error
        ):
            yield _sse({"type": "plan_ready"})

        yield _sse({"type": "done"})
    except ValueError as cfg_err:
        yield _sse({"type": "error", "error": str(cfg_err)})
        yield _sse({"type": "done"})
    except asyncio.CancelledError:
        cancel_event.set()
        raise
    except Exception as unexpected:
        yield _sse({"type": "error", "error": f"Внутренняя ошибка агента: {unexpected}"})
        yield _sse({"type": "done"})
    finally:
        cancel_event.set()
        if active_cancel_events.get(session_id) is cancel_event:
            active_cancel_events.pop(session_id, None)
        if cli is not None:
            try:
                await cli.close()
            except Exception:
                pass

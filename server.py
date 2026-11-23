import asyncio
import json
import os
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env", override=True)

API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ABLIT_KEY", "ak_nNTjWzWkiy_iG4-1vM3b1evpaGeHqNl04UWMs60bW5E")
ADMIN_KEY = os.getenv("ADMIN_KEY", "sk_siIKQ6JtgYIjSp3jRE7ow3rk0sOD2XdWYi5sXrA1mGDRgd")
BASE_URL = os.getenv("BASE_URL", "https://api.abliteration.ai/v1")
PORT = int(os.getenv("PORT", 5051))

def get_client() -> OpenAI:
    load_dotenv(Path(__file__).parent / ".env", override=True)
    base_url = os.getenv("BASE_URL", BASE_URL)
    k = os.getenv("OPENROUTER_API_KEY") or os.getenv("ABLIT_KEY", API_KEY)
    headers = {}
    if "openrouter.ai" in base_url or (k and k.startswith("sk-or-")):
        headers = {
            "HTTP-Referer": "http://localhost:5051",
            "X-Title": "NanoAgent Distiller"
        }
    return OpenAI(base_url=base_url, api_key=k, default_headers=headers)

client = get_client()

app = FastAPI(title="NanoAgent Context Distiller")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
SESSIONS_DIR = Path(__file__).parent / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SYSTEM_PROMPT_FILE = Path(__file__).parent / "system_prompt.txt"

DEFAULT_SYSTEM_PROMPT = (
    "Ты персональный AI-ассистент и технический консультант с доступом к локальному bash-терминалу Linux.\n\n"
    "ВАЖНЕЙШИЕ ПРАВИЛА ВЗАИМОДЕЙСТВИЯ С ПОЛЬЗОВАТЕЛЕМ:\n\n"
    "1. РЕЖИМ РАССУЖДЕНИЙ И ПЛАНИРОВАНИЯ (ПО УМОЛЧАНИЮ):\n"
    "   - Если пользователь задаёт вопрос, советуется, обсуждает архитектуру, исследует варианты или просит объяснить ситуацию — "
    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО сразу вызывать инструмент bash и бежать выполнять команды!\n"
    "   - Сначала подробно рассуждай: объясни суть, покажи альтернативы, разложи плюсы и минусы, сформируй четкий пошаговый план решения.\n"
    "   - В конце своего ответа всегда прямо спроси пользователя: 'Приступаем к выполнению плана? (или хочешь что-то скорректировать?)'.\n\n"
    "2. РЕЖИМ ВЫПОЛНЕНИЯ (ТОЛЬКО ПОСЛЕ ПОДТВЕРЖДЕНИЯ):\n"
    "   - Вызывай инструмент bash ТОЛЬКО тогда, когда пользователь дал явное подтверждение или прямое указание действовать "
    "(например: 'делай', 'выполняй', 'приступай', 'да', 'запусти команду', 'проверь в терминале').\n"
    "   - Не выполняй всё скопом без остановки: делай логический шаг, оценивай результат и держи пользователя в курсе.\n"
    "   - Перед опасными действиями (удаление, перезагрузка служб, изменение системных конфигов) обязательно покажи точную команду и предупреди о последствиях.\n\n"
    "3. СТИЛЬ И ЯЗЫК:\n"
    "   - Отвечай грамотно, структурированно, профессионально и на русском языке."
)

def get_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE.exists():
        try:
            txt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
            if txt:
                return txt
        except Exception:
            pass
    return DEFAULT_SYSTEM_PROMPT

SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT

DISTILLER_SYSTEM_PROMPT = (
    "Ты — специализированный ИИ-дистиллятор контекста и архитектор рабочей памяти автономного агента. "
    "Твоя цель — проанализировать массивную историю диалога, команды bash, выводы терминала и промежуточные гипотезы, "
    "и выделить из них СУХУЮ КВИНТЭССЕНЦИЮ. Никаких приветствий, никакой воды.\n"
    "Сформируй рабочую память строго по блокам:\n"
    "### 🎯 Целевая задача пользователя:\n"
    "Кратко суть решаемой проблемы.\n\n"
    "### 📌 Подтверждённые факты и окружение:\n"
    "Точные IP, порты, обнаруженные токены, пути, ID устройств, версии, статусы.\n\n"
    "### ❌ Что проверено и НЕ сработало:\n"
    "Какие эндпоинты/команды выдали ошибку (чтобы агент не повторял попыток).\n\n"
    "### ⏳ Текущий статус и следующий шаг:\n"
    "На чём именно остановились и что конкретно нужно сделать дальше.\n"
)

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Execute a bash shell command on the local machine and get stdout/stderr.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact shell command to execute"
                }
            },
            "required": ["command"]
        }
    }
}

total_tokens_used = 0


def fetch_balance() -> Optional[str]:
    load_dotenv(Path(__file__).parent / ".env", override=True)
    base_url = os.getenv("BASE_URL", BASE_URL)
    k = os.getenv("OPENROUTER_API_KEY") or os.getenv("ABLIT_KEY", API_KEY)
    adm_k = os.getenv("ADMIN_KEY", ADMIN_KEY)

    if "openrouter.ai" in base_url or (k and k.startswith("sk-or-")):
        try:
            url = "https://openrouter.ai/api/v1/credits"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {k}"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                d = data.get("data", {})
                tot = float(d.get("total_credits", 0))
                usage = float(d.get("total_usage", 0))
                remaining = max(0.0, tot - usage)
                return f"${remaining:.4f}"
        except Exception as e:
            print("Ошибка получения баланса OpenRouter:", e)
            return None
    elif adm_k:
        try:
            url = "https://api.abliteration.ai/v1/organization/balance"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {adm_k}"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                avail = float(data.get("available_usd", 0))
                return f"${avail:.4f}"
        except Exception as e:
            print("Ошибка получения баланса:", e)
            return None
    return None


def get_session_file(session_id: str) -> Path:
    clean_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return SESSIONS_DIR / f"{clean_id}.json"


def save_session(session: dict):
    path = get_session_file(session["id"])
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session(session_id: str) -> Optional[dict]:
    path = get_session_file(session_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def calculate_session_tokens(session: dict) -> int:
    total_chars = len(SYSTEM_PROMPT)
    for m in session.get("messages", []):
        total_chars += len(m.get("content") or "")
        if m.get("tool_calls"):
            total_chars += len(json.dumps(m["tool_calls"]))
    return int(total_chars / 3.5)


def list_sessions() -> List[dict]:
    res = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            res.append({
                "id": data.get("id"),
                "title": data.get("title", "Без названия"),
                "created_at": data.get("created_at", 0),
                "updated_at": data.get("updated_at", 0),
                "messages_count": len(data.get("messages", [])),
                "tokens": calculate_session_tokens(data)
            })
        except Exception:
            pass
    res.sort(key=lambda x: x["updated_at"], reverse=True)
    return res


def create_new_session(title: str = "Новый диалог (Дистиллятор)") -> dict:
    session_id = str(uuid.uuid4())[:8]
    now = int(time.time())
    session = {
        "id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": []
    }
    save_session(session)
    return session


def run_bash_cmd(cmd: str) -> str:
    try:
        is_win = os.name == "nt"
        if is_win:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120
            )
        else:
            proc = subprocess.run(
                cmd,
                shell=True,
                executable="/bin/bash" if os.path.exists("/bin/bash") else None,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120
            )
        out = proc.stdout
        err = proc.stderr
        res = ""
        if out:
            res += out
        if err:
            if res:
                res += "\n"
            res += f"[stderr]:\n{err}"
        if proc.returncode != 0:
            res += f"\n[exit code: {proc.returncode}]"
        return res if res else "[пустой вывод / success]"
    except subprocess.TimeoutExpired:
        return "[ошибка: таймаут команды (120 сек)]"
    except Exception as e:
        return f"[ошибка выполнения: {str(e)}]"


# --- Asynchronous Background Gemini Consolidator ---

session_distill_status: Dict[str, dict] = {}
session_distill_locks: Dict[str, asyncio.Lock] = {}


def get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in session_distill_locks:
        session_distill_locks[session_id] = asyncio.Lock()
    return session_distill_locks[session_id]


async def background_gemini_consolidator(session_id: str):
    lock = get_session_lock(session_id)
    if lock.locked():
        return

    async with lock:
        session = load_session(session_id)
        if not session:
            return

        msgs = session.get("messages", [])
        if len(msgs) < 3:
            return

        user_indices = [i for i, m in enumerate(msgs) if m.get("role") == "user"]
        if not user_indices:
            return

        # Keep recent messages for context continuity, distill earlier history
        if len(user_indices) > 1:
            split_idx = user_indices[-1]
            history_to_compress = msgs[:split_idx]
            keep_suffix = msgs[split_idx:]
        else:
            if len(msgs) > 6:
                history_to_compress = msgs[:-4]
                keep_suffix = msgs[-4:]
            else:
                history_to_compress = msgs
                keep_suffix = []

        if not history_to_compress:
            return

        tokens_before = calculate_session_tokens(session)
        session_distill_status[session_id] = {
            "status": "running",
            "tokens_before": tokens_before,
            "turns_count": len(history_to_compress),
            "started_at": int(time.time()),
            "partial_text": ""
        }

        formatted = []
        for m in history_to_compress:
            r = m.get("role")
            if r == "user":
                formatted.append(f"👤 [Пользователь]: {m.get('content')}")
            elif r == "assistant":
                txt = m.get("content") or ""
                if m.get("tool_calls"):
                    cmds = []
                    for tc in m["tool_calls"]:
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            cmds.append(args.get("command", ""))
                        except Exception:
                            cmds.append(tc.get("function", {}).get("arguments", ""))
                    formatted.append(f"🤖 [Ассистент вызвал bash]:\n" + "\n".join(cmds))
                if txt:
                    formatted.append(f"🤖 [Ассистент]:\n{txt[:400]}")
            elif r == "tool":
                cmd = m.get("command") or ""
                out = (m.get("content") or "")[:350]
                formatted.append(f"💻 [Вывод команды '{cmd}']:\n{out}")

        clean_history = "\n\n".join(formatted)
        if len(clean_history) > 45000:
            clean_history = "[...более ранние этапы сжаты...]\n\n" + clean_history[-45000:]

        gemini_prompt = (
            f"{DISTILLER_SYSTEM_PROMPT}\n\n"
            f"Вот хронология работы локального агента:\n\n{clean_history}\n\n"
            f"Выдели суть, добавь все новые подтверждённые факты и убери отработанные ошибки. Сформируй 'Рабочую память' (Active Memory) строго по шаблону."
        )

        try:
            cli = get_client()
            distill_model = "deepseek/deepseek-v4.1-flash" if is_openrouter else "abliterated-model-large-flash"

            def run_distill():
                return cli.chat.completions.create(
                    model=distill_model,
                    messages=[
                        {"role": "system", "content": DISTILLER_SYSTEM_PROMPT},
                        {"role": "user", "content": gemini_prompt}
                    ],
                    stream=True,
                    max_tokens=2000
                )

            stream = await asyncio.to_thread(run_distill)
            full_distillation = ""

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_distillation += delta
                    session_distill_status[session_id]["partial_text"] = full_distillation
                    await asyncio.sleep(0.001)

            if full_distillation.strip():
                # Re-load session to merge cleanly with messages added while Distiller ran
                latest_session = load_session(session_id) or session
                curr_msgs = latest_session.get("messages", [])

                recent_msgs = curr_msgs[len(history_to_compress):] if len(curr_msgs) >= len(history_to_compress) else keep_suffix

                memory_user_msg = {
                    "role": "user",
                    "content": f"[🧠 ДИСТИЛЛИРОВАННАЯ РАБОЧАЯ ПАМЯТЬ АГЕНТА]\n{full_distillation.strip()}",
                    "is_distilled_memory": True
                }
                memory_assistant_ack = {
                    "role": "assistant",
                    "content": "Принято. Фоновая рабочая память обновлена. Все факты и задачи актуализированы.",
                    "is_distilled_ack": True
                }

                latest_session["active_memory"] = full_distillation.strip()
                latest_session["messages"] = [memory_user_msg, memory_assistant_ack] + recent_msgs
                latest_session["updated_at"] = int(time.time())
                save_session(latest_session)

                tokens_after = calculate_session_tokens(latest_session)
                saved_tokens = max(0, tokens_before - tokens_after)
                saved_pct = round((saved_tokens / max(1, tokens_before)) * 100, 1)

                session_distill_status[session_id] = {
                    "status": "done",
                    "summary": full_distillation.strip(),
                    "tokens_before": tokens_before,
                    "tokens_after": tokens_after,
                    "saved_tokens": saved_tokens,
                    "saved_percent": saved_pct,
                    "finished_at": int(time.time())
                }
            else:
                session_distill_status[session_id] = {"status": "error", "error": "Пустой ответ дистиллятора"}
        except Exception as e:
            print("Ошибка фоновой дистилляции:", e)
            session_distill_status[session_id] = {"status": "error", "error": str(e)}


# --- Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/status")
async def get_status():
    global total_tokens_used
    cwd = os.getcwd()
    balance = fetch_balance()
    load_dotenv(Path(__file__).parent / ".env", override=True)
    base_url = os.getenv("BASE_URL", BASE_URL)
    k = os.getenv("OPENROUTER_API_KEY") or os.getenv("ABLIT_KEY", API_KEY)
    is_openrouter = "openrouter.ai" in base_url or (k and k.startswith("sk-or-"))

    if is_openrouter:
        models = [
            {
                "id": "deepseek/deepseek-v4.1-flash",
                "name": "DeepSeek V4.1 Flash",
                "short_name": "Flash 1M",
                "icon": "⚡",
                "badge": "🚀 480 т/с",
                "context": "1M контекст",
                "desc": "Ультрабыстрый отклик, идеальна для кода и консоли"
            },
            {
                "id": "meta-llama/llama-3.3-70b-instruct",
                "name": "Llama 3.3 70B Instruct",
                "short_name": "Llama 3.3",
                "icon": "🦙",
                "badge": "⚡ Отклик 0.6с",
                "context": "128k контекст",
                "desc": "Высокая скорость и глубокое понимание контекста"
            },
            {
                "id": "qwen/qwen-2.5-72b-instruct",
                "name": "Qwen 2.5 72B Instruct",
                "short_name": "Qwen 2.5",
                "icon": "💻",
                "badge": "💻 Код и архитектура",
                "context": "128k контекст",
                "desc": "Мощная открытая модель для программирования"
            },
            {
                "id": "deepseek/deepseek-chat",
                "name": "DeepSeek V3 (Chat)",
                "short_name": "DeepSeek V3",
                "icon": "🧠",
                "badge": "Баланс",
                "context": "64k контекст",
                "desc": "Универсальный стандарт для диалогов и задач"
            },
            {
                "id": "deepseek/deepseek-r1",
                "name": "DeepSeek R1 (Reasoning)",
                "short_name": "DeepSeek R1",
                "icon": "🔬",
                "badge": "Рассуждения CoT",
                "context": "164k контекст",
                "desc": "Глубокие пошаговые рассуждения перед ответом"
            }
        ]
    else:
        models = [
            {
                "id": "abliterated-model-large-flash",
                "name": "Flash 1M (DeepSeek V4.1 Flash)",
                "short_name": "Flash 1M",
                "icon": "⚡",
                "badge": "🚀 Быстрая (Рекомендуется)",
                "context": "1M контекст",
                "desc": "Ультрабыстрая разблокированная модель, 1M токенов, идеальна для кода и команд"
            },
            {
                "id": "abliterated-model",
                "name": "Qwen 3.5 (Abliterated)",
                "short_name": "Qwen 3.5",
                "icon": "🧠",
                "badge": "⚖️ Баланс",
                "context": "256k контекст",
                "desc": "Сбалансированная модель на базе Qwen 3.5, глубокая логика и точность"
            },
            {
                "id": "abliterated-model-large-v2",
                "name": "GLM-5.3 Large v2",
                "short_name": "GLM-5.3 Large",
                "icon": "🏋️",
                "badge": "🔥 Мощная (Large)",
                "context": "1M контекст",
                "desc": "Тяжелая флагманская модель с огромным контекстом для сложного анализа"
            },
            {
                "id": "abliterated-model-large",
                "name": "Abliterated Large v1",
                "short_name": "Large v1",
                "icon": "⭐",
                "badge": "Классика",
                "context": "1M контекст",
                "desc": "Предыдущая ревизия 1M Large модели"
            }
        ]

    return {
        "status": "ok",
        "provider": "openrouter" if is_openrouter else "abliteration",
        "mode": "Context Distiller (Параллельный хост 5051)",
        "cwd": cwd,
        "balance": balance,
        "total_tokens": total_tokens_used,
        "models": models
    }


class ConfigUpdateRequest(BaseModel):
    provider: str = "abliteration"  # "abliteration", "openrouter", "custom"
    api_key: str
    base_url: Optional[str] = None
    admin_key: Optional[str] = None


@app.get("/api/config")
async def get_config():
    env_file = Path(__file__).parent / ".env"
    load_dotenv(env_file, override=True)
    b_url = os.getenv("BASE_URL", BASE_URL)
    k = os.getenv("OPENROUTER_API_KEY") or os.getenv("ABLIT_KEY", API_KEY)
    adm = os.getenv("ADMIN_KEY", "")
    is_or = "openrouter.ai" in b_url or (k and k.startswith("sk-or-"))
    prov = "openrouter" if is_or else ("custom" if "abliteration.ai" not in b_url else "abliteration")
    masked_key = (k[:6] + "..." + k[-4:]) if (k and len(k) > 10) else ("***" if k else "")
    bal = fetch_balance()
    return {
        "has_key": bool(k and len(k) > 5),
        "provider": prov,
        "base_url": b_url,
        "masked_key": masked_key,
        "has_admin_key": bool(adm),
        "balance": bal
    }


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    env_file = Path(__file__).parent / ".env"
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API-ключ не может быть пустым")

    if req.provider == "openrouter":
        b_url = "https://openrouter.ai/api/v1"
        ab_key = ""
        or_key = key
        adm_key = req.admin_key.strip() if req.admin_key else ""
    elif req.provider == "custom":
        b_url = (req.base_url or "https://api.abliteration.ai/v1").strip()
        ab_key = key
        or_key = ""
        adm_key = req.admin_key.strip() if req.admin_key else ""
    else:  # abliteration
        b_url = "https://api.abliteration.ai/v1"
        ab_key = key
        or_key = ""
        adm_key = req.admin_key.strip() if req.admin_key else ""

    lines = [
        f"BASE_URL={b_url}",
        f"ABLIT_KEY={ab_key}",
        f"OPENROUTER_API_KEY={or_key}",
        f"ADMIN_KEY={adm_key}",
        f"PORT=5051"
    ]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    load_dotenv(env_file, override=True)
    bal = fetch_balance()
    return {"status": "ok", "message": "Настройки успешно сохранены", "balance": bal}


@app.get("/api/sessions")
async def get_sessions():
    sessions = list_sessions()
    if not sessions:
        new_s = create_new_session()
        sessions = [new_s]
    return sessions


@app.post("/api/sessions/new")
async def post_new_session():
    return create_new_session()


@app.get("/api/sessions/{session_id}")
async def get_single_session(session_id: str):
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    session["tokens"] = calculate_session_tokens(session)
    return session


@app.delete("/api/sessions/{session_id}")
async def delete_single_session(session_id: str):
    path = get_session_file(session_id)
    if path.exists():
        path.unlink()
    return {"status": "deleted"}


class ManualDistillRequest(BaseModel):
    session_id: str


@app.post("/api/distill")
async def manual_distill(req: ManualDistillRequest):
    session = load_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    st = session_distill_status.get(req.session_id, {})
    if st.get("status") == "running":
        return {"status": "running", "message": "Фоновая дистилляция уже выполняется"}

    asyncio.create_task(background_gemini_consolidator(req.session_id))
    return {"status": "started", "message": "Фоновая дистилляция Gemini запущена параллельно"}


@app.get("/api/distill/status/{session_id}")
async def get_distill_status(session_id: str):
    return session_distill_status.get(session_id, {"status": "idle"})


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: str = "abliterated-model-large-flash"
    reasoning_effort: str = "low"
    context_limit: int = 32000
    compress_threshold: float = 0.50  # 50% threshold for intelligent distillation


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    global total_tokens_used

    session_id = req.session_id
    session = load_session(session_id) if session_id else None
    if not session:
        session = create_new_session(title=req.message[:35] + ("..." if len(req.message) > 35 else ""))
        session_id = session["id"]

    user_text = req.message.strip()
    session["messages"].append({"role": "user", "content": user_text})
    if session.get("title") == "Новый диалог (Дистиллятор)" and user_text:
        session["title"] = user_text[:35] + ("..." if len(user_text) > 35 else "")
    session["updated_at"] = int(time.time())
    save_session(session)

    async def event_generator() -> AsyncGenerator[str, None]:
        global total_tokens_used

        current_ctx_tokens = calculate_session_tokens(session)
        yield f"data: {json.dumps({'type': 'session_init', 'session_id': session_id, 'title': session['title'], 'context_tokens': current_ctx_tokens, 'context_limit': req.context_limit}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)

        # 🧠 Background auto-distillation: runs completely in background, chat never freezes!
        threshold_tokens = int(req.context_limit * req.compress_threshold)
        if current_ctx_tokens >= threshold_tokens and len(session["messages"]) >= 4:
            st = session_distill_status.get(session_id, {})
            if st.get("status") != "running":
                asyncio.create_task(background_gemini_consolidator(session_id))
                yield f"data: {json.dumps({'type': 'status', 'text': '🧠 Фоновый дистиллятор Gemini запущен параллельно...'}, ensure_ascii=False)}\n\n"

        # Prepare messages for Main Agent with Active Memory injected into the System Prompt
        system_content = get_system_prompt()
        active_mem = session.get("active_memory")
        if not active_mem:
            for m in session.get("messages", []):
                if m.get("is_distilled_memory") or "[🧠 ДИСТИЛЛИРОВАННАЯ" in (m.get("content") or ""):
                    active_mem = m.get("content")
                    break

        if active_mem:
            system_content += (
                "\n\n=======================================================\n"
                "🧠 АКТУАЛЬНАЯ РАБОЧАЯ ПАМЯТЬ АГЕНТА (ACTIVE MEMORY):\n"
                f"{active_mem}\n"
                "=======================================================\n"
                "ВАЖНОЕ ПРАВИЛО: Выше представлена твоя актуализированная рабочая память. "
                "Ты ОБЯЗАН опираться на зафиксированные в ней факты, IP-адреса, токены, пароли и результаты. "
                "Никогда не повторяй команды и подходы, помеченные в блоке 'Что проверено и НЕ сработало'. "
                "Продолжай решение задачи строго с зафиксированного 'Текущего статуса и следующего шага'."
            )

        api_messages = [{"role": "system", "content": system_content}]
        for m in session["messages"]:
            # If already injected in system prompt, skip duplicate in chat history
            if m.get("is_distilled_memory") or m.get("is_distilled_ack"):
                continue
            role = m["role"]
            if role == "user":
                api_messages.append({"role": "user", "content": m["content"]})
            elif role == "assistant":
                item = {"role": "assistant", "content": m.get("content")}
                if m.get("tool_calls"):
                    item["tool_calls"] = m["tool_calls"]
                api_messages.append(item)
            elif role == "tool":
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id"),
                    "content": m.get("content")
                })

        max_iterations = 25
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            extra_params = {}
            if req.reasoning_effort in ("low", "high", "max") and any(x in req.model for x in ("deepseek-r1", "o1", "o3", "abliterated")):
                extra_params["reasoning_effort"] = req.reasoning_effort

            yield f"data: {json.dumps({'type': 'status', 'text': 'Отправляю запрос к модели...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)

            try:
                cli = get_client()
                def get_stream():
                    return cli.chat.completions.create(
                        model=req.model,
                        messages=api_messages,
                        tools=[BASH_TOOL],
                        tool_choice="auto",
                        stream=True,
                        stream_options={"include_usage": True},
                        **extra_params
                    )
                stream = await asyncio.to_thread(get_stream)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
                return

            full_content = ""
            full_reasoning = ""
            tools_map = {}
            last_usage = None

            for chunk in stream:
                if chunk.usage:
                    last_usage = chunk.usage

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Reasoning stream
                reasoning = getattr(delta, 'reasoning_content', None) or getattr(delta, 'reasoning', None)
                if reasoning:
                    full_reasoning += reasoning
                    yield f"data: {json.dumps({'type': 'reasoning', 'delta': reasoning}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.005)

                # Content stream
                if delta.content:
                    full_content += delta.content
                    yield f"data: {json.dumps({'type': 'content', 'delta': delta.content}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.005)

                # Tool call chunks
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tools_map:
                            tools_map[idx] = {
                                "id": tc.id or "",
                                "name": (tc.function.name if tc.function else "") or "",
                                "arguments": ""
                            }
                        if tc.id:
                            tools_map[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tools_map[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tools_map[idx]["arguments"] += tc.function.arguments

            if last_usage:
                total_tokens_used += last_usage.total_tokens
                balance = await asyncio.to_thread(fetch_balance)
                ctx_toks = calculate_session_tokens(session)
                yield f"data: {json.dumps({'type': 'usage', 'prompt': last_usage.prompt_tokens, 'completion': last_usage.completion_tokens, 'total': last_usage.total_tokens, 'grand_total': total_tokens_used, 'balance': balance, 'context_tokens': ctx_toks, 'context_limit': req.context_limit})}\n\n"

            if tools_map:
                tool_calls_list = [
                    {
                        "id": v["id"] or f"call_{i}",
                        "type": "function",
                        "function": {
                            "name": v["name"] or "bash",
                            "arguments": v["arguments"]
                        }
                    } for i, v in sorted(tools_map.items())
                ]

                asst_entry = {
                    "role": "assistant",
                    "content": full_content or None,
                    "reasoning": full_reasoning or None,
                    "tool_calls": tool_calls_list
                }
                api_messages.append({
                    "role": "assistant",
                    "content": full_content or None,
                    "tool_calls": tool_calls_list
                })
                session["messages"].append(asst_entry)
                session["updated_at"] = int(time.time())
                save_session(session)

                for tc in tool_calls_list:
                    fn_name = tc["function"]["name"]
                    args_raw = tc["function"]["arguments"]
                    try:
                        args = json.loads(args_raw)
                        cmd = args.get("command", "")
                    except Exception:
                        cmd = args_raw

                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': fn_name, 'command': cmd}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)

                    output = await asyncio.to_thread(run_bash_cmd, cmd)

                    yield f"data: {json.dumps({'type': 'tool_done', 'tool': fn_name, 'command': cmd, 'output': output}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)

                    tool_resp = {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "command": cmd,
                        "content": output
                    }
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": output
                    })
                    session["messages"].append(tool_resp)
                    session["updated_at"] = int(time.time())
                    save_session(session)

                loop_ctx_tokens = calculate_session_tokens(session)
                if loop_ctx_tokens >= threshold_tokens and len(session["messages"]) >= 6:
                    st = session_distill_status.get(session_id, {})
                    if st.get("status") != "running":
                        asyncio.create_task(background_gemini_consolidator(session_id))
                        yield f"data: {json.dumps({'type': 'status', 'text': '🧠 Фоновый дистиллятор запущен параллельно...'}, ensure_ascii=False)}\n\n"

                continue
            else:
                if full_content:
                    session["messages"].append({
                        "role": "assistant",
                        "content": full_content,
                        "reasoning": full_reasoning or None
                    })
                    session["updated_at"] = int(time.time())
                    save_session(session)
                break

        # If loop reached max_iterations and ends on tool output without assistant conclusion
        if session["messages"] and session["messages"][-1].get("role") == "tool":
            yield f"data: {json.dumps({'type': 'status', 'text': 'Подвожу итог работы...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)
            try:
                cli = get_client()
                def get_final_stream():
                    return cli.chat.completions.create(
                        model=req.model,
                        messages=api_messages,
                        tool_choice="none",
                        stream=True,
                        **extra_params
                    )
                final_stream = await asyncio.to_thread(get_final_stream)
                final_content = ""
                final_reasoning = ""
                for chunk in final_stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    reasoning = getattr(delta, 'reasoning_content', None) or getattr(delta, 'reasoning', None)
                    if reasoning:
                        final_reasoning += reasoning
                        yield f"data: {json.dumps({'type': 'reasoning', 'delta': reasoning}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.005)
                    if delta.content:
                        final_content += delta.content
                        yield f"data: {json.dumps({'type': 'content', 'delta': delta.content}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.005)

                if final_content:
                    session["messages"].append({
                        "role": "assistant",
                        "content": final_content,
                        "reasoning": final_reasoning or None
                    })
                    session["updated_at"] = int(time.time())
                    save_session(session)
            except Exception as e:
                err_msg = f"\n[Все действия выполнены. Ответ завершён: {e}]"
                session["messages"].append({"role": "assistant", "content": err_msg})
                session["updated_at"] = int(time.time())
                save_session(session)
                yield f"data: {json.dumps({'type': 'content', 'delta': err_msg}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Запуск NanoAgent Context Distiller на http://localhost:{PORT}")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False)

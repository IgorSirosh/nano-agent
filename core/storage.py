import asyncio
import json
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.config import BASE_DIR, load_base_system_prompt

SESSIONS_DIR = BASE_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

_session_locks: Dict[str, asyncio.Lock] = {}


def get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


def default_cwd() -> str:
    env_cwd = os.environ.get("DEFAULT_CWD")
    if env_cwd and Path(env_cwd).is_dir():
        return env_cwd
    ws = os.environ.get("AGENT_WORKSPACE")
    if ws:
        ws_path = Path(ws).resolve()
        ws_path.mkdir(parents=True, exist_ok=True)
        return str(ws_path)
    local_ws = (BASE_DIR / "workspace").resolve()
    local_ws.mkdir(parents=True, exist_ok=True)
    return str(local_ws)


def estimate_tokens(text: Optional[str]) -> int:
    if not text:
        return 0
    non_ascii = sum(1 for c in text if ord(c) > 127)
    ascii_cnt = len(text) - non_ascii
    toks = (non_ascii / 1.8) + (ascii_cnt / 4.0)
    return max(1, int(math.ceil(toks)))


def calculate_active_tokens(session: dict, system_prompt_text: Optional[str] = None) -> int:
    sys_txt = system_prompt_text if system_prompt_text is not None else load_base_system_prompt()
    total = estimate_tokens(sys_txt)
    total += estimate_tokens(session.get("active_memory") or "")
    for m in session.get("messages", []):
        if m.get("compressed"):
            continue
        if m.get("is_distilled_memory") or m.get("is_distilled_ack"):
            continue
        if m.get("role") not in ("user", "assistant", "tool"):
            continue
        total += estimate_tokens(m.get("content") or "")
        if m.get("tool_calls"):
            total += estimate_tokens(json.dumps(m["tool_calls"], ensure_ascii=False))
        total += 4  # per-message framing overhead
    return total


def get_session_file(session_id: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    clean_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    if not clean_id:
        clean_id = "default"
    return SESSIONS_DIR / f"{clean_id}.json"


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def normalize_session(raw: dict) -> dict:
    now = int(time.time())
    session = dict(raw) if isinstance(raw, dict) else {}

    session.setdefault("id", str(uuid.uuid4())[:8])
    session.setdefault("title", "Новый диалог")
    session.setdefault("created_at", now)
    session.setdefault("updated_at", session["created_at"])

    raw_cwd = session.get("cwd")
    if not raw_cwd or not isinstance(raw_cwd, str) or not Path(raw_cwd).is_dir():
        session["cwd"] = default_cwd()

    mode = session.get("mode", "plan")
    session["mode"] = mode if mode in ("plan", "act") else "plan"

    session.setdefault("active_memory", "")
    stats = session.get("stats")
    if not isinstance(stats, dict):
        stats = {}
    session["stats"] = {
        "prompt_tokens": int(stats.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(stats.get("completion_tokens", 0) or 0),
        "total_tokens": int(stats.get("total_tokens", 0) or 0),
        "distill_count": int(stats.get("distill_count", 0) or 0),
        "saved_tokens": int(stats.get("saved_tokens", 0) or 0),
    }

    messages = session.get("messages")
    if not isinstance(messages, list):
        messages = []

    migrated_memory = session["active_memory"]
    norm_msgs: List[dict] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        item = dict(m)
        if not item.get("msg_id"):
            item["msg_id"] = uuid.uuid4().hex[:10]
        if "compressed" not in item:
            item["compressed"] = False

        content_str = item.get("content") or ""
        is_legacy_mem = bool(item.get("is_distilled_memory")) or (
            item.get("role") == "user" and "[🧠 ДИСТИЛЛИРОВАННАЯ" in content_str
        )
        is_legacy_ack = bool(item.get("is_distilled_ack"))

        if is_legacy_mem:
            extracted = content_str.replace("[🧠 ДИСТИЛЛИРОВАННАЯ РАБОЧАЯ ПАМЯТЬ АГЕНТА]", "").strip()
            if not migrated_memory and extracted:
                migrated_memory = extracted
            item["compressed"] = True
        elif is_legacy_ack:
            item["compressed"] = True

        norm_msgs.append(item)

    session["active_memory"] = migrated_memory
    session["messages"] = norm_msgs
    return session


def _read_session_sync(session_id: str) -> Optional[dict]:
    path = get_session_file(session_id)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return normalize_session(raw)
    except Exception:
        return None


async def create_session(
    title: str = "Новый диалог",
    cwd: Optional[str] = None,
    mode: str = "plan",
) -> dict:
    session_id = str(uuid.uuid4())[:8]
    now = int(time.time())
    valid_cwd = cwd if (cwd and Path(cwd).is_dir()) else default_cwd()
    valid_mode = mode if mode in ("plan", "act") else "plan"

    session = normalize_session(
        {
            "id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "cwd": valid_cwd,
            "mode": valid_mode,
            "active_memory": "",
            "messages": [],
        }
    )
    async with get_session_lock(session_id):
        _atomic_write_json(get_session_file(session_id), session)
    return session


async def get_session(session_id: str) -> Optional[dict]:
    async with get_session_lock(session_id):
        return _read_session_sync(session_id)


async def list_all_sessions() -> List[dict]:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    res: List[dict] = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            s = normalize_session(raw)
            visible_msgs = [
                m
                for m in s["messages"]
                if not m.get("is_distilled_ack") and m.get("role") != "system_event"
            ]
            res.append(
                {
                    "id": s["id"],
                    "title": s["title"],
                    "cwd": s["cwd"],
                    "mode": s["mode"],
                    "created_at": s["created_at"],
                    "updated_at": s["updated_at"],
                    "messages_count": len(visible_msgs),
                    "tokens": calculate_active_tokens(s),
                    "has_memory": bool(s.get("active_memory")),
                }
            )
        except Exception:
            pass
    res.sort(key=lambda x: x["updated_at"], reverse=True)
    return res


async def update_session_fields(session_id: str, **fields: Any) -> Optional[dict]:
    async with get_session_lock(session_id):
        session = _read_session_sync(session_id)
        if not session:
            return None
        for k, v in fields.items():
            if k == "title" and isinstance(v, str) and v.strip():
                session["title"] = v.strip()[:120]
            elif k == "mode" and v in ("plan", "act"):
                session["mode"] = v
            elif k == "cwd" and isinstance(v, str):
                p = Path(v).expanduser()
                if p.exists() and p.is_dir():
                    session["cwd"] = str(p.resolve())
                else:
                    raise ValueError(f"Директория не существует: {v}")
        session["updated_at"] = int(time.time())
        _atomic_write_json(get_session_file(session_id), session)
        return session


async def append_session_message(session_id: str, msg: dict) -> Optional[dict]:
    async with get_session_lock(session_id):
        session = _read_session_sync(session_id)
        if not session:
            return None
        entry = dict(msg)
        entry.setdefault("msg_id", uuid.uuid4().hex[:10])
        entry.setdefault("ts", int(time.time()))
        entry.setdefault("compressed", False)
        session["messages"].append(entry)
        session["updated_at"] = int(time.time())
        _atomic_write_json(get_session_file(session_id), session)
        return session


async def update_session_stats(
    session_id: str,
    prompt_delta: int = 0,
    completion_delta: int = 0,
    total_delta: int = 0,
) -> Optional[dict]:
    async with get_session_lock(session_id):
        session = _read_session_sync(session_id)
        if not session:
            return None
        st = session["stats"]
        st["prompt_tokens"] += int(prompt_delta or 0)
        st["completion_tokens"] += int(completion_delta or 0)
        st["total_tokens"] += int(total_delta or 0)
        _atomic_write_json(get_session_file(session_id), session)
        return session


async def commit_distillation(
    session_id: str,
    compressed_ids: Set[str],
    new_memory: str,
    tokens_before: int,
    engine_label: str = "Gemini 3.8 Flash · $0",
) -> Optional[dict]:
    async with get_session_lock(session_id):
        session = _read_session_sync(session_id)
        if not session:
            return None

        for m in session["messages"]:
            if m.get("msg_id") in compressed_ids:
                m["compressed"] = True

        session["active_memory"] = new_memory.strip()
        tokens_after = calculate_active_tokens(session)
        saved_tokens = max(0, tokens_before - tokens_after)
        saved_pct = round((saved_tokens / max(1, tokens_before)) * 100, 1)

        event_msg = {
            "msg_id": uuid.uuid4().hex[:10],
            "role": "system_event",
            "event": "distilled",
            "ts": int(time.time()),
            "compressed": False,
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "saved_tokens": saved_tokens,
            "saved_percent": saved_pct,
            "compressed_count": len(compressed_ids),
            "engine_label": engine_label,
            "summary": session["active_memory"],
        }
        session["messages"].append(event_msg)

        session["stats"]["distill_count"] += 1
        session["stats"]["saved_tokens"] += saved_tokens
        session["updated_at"] = int(time.time())
        _atomic_write_json(get_session_file(session_id), session)

        return {
            "session": session,
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "saved_tokens": saved_tokens,
            "saved_percent": saved_pct,
            "engine_label": engine_label,
            "summary": session["active_memory"],
        }


async def delete_session(session_id: str) -> bool:
    async with get_session_lock(session_id):
        path = get_session_file(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

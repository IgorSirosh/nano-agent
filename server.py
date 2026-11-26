import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.agent import (
    chat_stream_generator,
    stop_session_execution,
    total_tokens_used_global,
)
from core.config import (
    BASE_DIR,
    DEFAULT_BASE_SYSTEM_PROMPT,
    fetch_balance_async,
    get_models_catalog,
    load_base_system_prompt,
    load_config,
    reset_base_system_prompt,
    save_base_system_prompt,
    save_config,
)
from core.context import distill_session_async, session_distill_status
from core.storage import (
    append_session_message,
    calculate_active_tokens,
    create_session,
    delete_session,
    get_session,
    list_all_sessions,
    update_session_fields,
)

STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="NanoAgent Context Distiller v2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ConfigUpdateRequest(BaseModel):
    provider: str = "abliteration"
    api_key: Optional[str] = ""
    base_url: Optional[str] = None
    admin_key: Optional[str] = None


class SystemPromptUpdateRequest(BaseModel):
    content: str


class NewSessionRequest(BaseModel):
    title: str = "Новый диалог"
    cwd: Optional[str] = None
    mode: str = "plan"


class SessionPatchRequest(BaseModel):
    title: Optional[str] = None
    mode: Optional[str] = None
    cwd: Optional[str] = None


class ManualDistillRequest(BaseModel):
    session_id: str
    model: Optional[str] = None


class StopRequest(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: str = "abliterated-model-large-flash"
    reasoning_effort: str = "low"
    context_limit: int = 32000
    compress_threshold: float = 0.50
    mode: Optional[str] = None
    approve_execution: bool = False


@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(
        content=index_file.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/api/status")
async def get_status():
    cfg = load_config()
    balance = await fetch_balance_async()
    models = get_models_catalog(cfg["provider"])
    return {
        "status": "ok",
        "version": "2.0",
        "provider": cfg["provider"],
        "port": cfg["port"],
        "has_key": cfg["has_key"],
        "mode": f"Context Distiller v2.0 (Порт {cfg['port']})",
        "cwd": os.getcwd(),
        "balance": balance,
        "total_tokens": total_tokens_used_global,
        "models": models,
    }


@app.get("/api/config")
async def get_config_endpoint():
    cfg = load_config()
    balance = await fetch_balance_async()
    return {
        "has_key": cfg["has_key"],
        "provider": cfg["provider"],
        "base_url": cfg["base_url"],
        "masked_key": cfg["masked_key"],
        "has_admin_key": cfg["has_admin_key"],
        "port": cfg["port"],
        "balance": balance,
    }


@app.post("/api/config")
async def update_config_endpoint(req: ConfigUpdateRequest):
    try:
        updated = save_config(
            provider=req.provider,
            api_key=req.api_key,
            base_url=req.base_url,
            admin_key=req.admin_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    balance = await fetch_balance_async(force=True)
    return {
        "status": "ok",
        "message": "Настройки успешно сохранены",
        "provider": updated["provider"],
        "has_key": updated["has_key"],
        "masked_key": updated["masked_key"],
        "has_admin_key": updated["has_admin_key"],
        "balance": balance,
    }


@app.get("/api/system-prompt")
async def get_system_prompt_endpoint():
    return {
        "content": load_base_system_prompt(),
        "default": DEFAULT_BASE_SYSTEM_PROMPT,
    }


@app.post("/api/system-prompt")
async def update_system_prompt_endpoint(req: SystemPromptUpdateRequest):
    try:
        saved = save_base_system_prompt(req.content)
        return {"status": "ok", "content": saved}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/system-prompt/reset")
async def reset_system_prompt_endpoint():
    saved = reset_base_system_prompt()
    return {"status": "ok", "content": saved}


@app.get("/api/sessions")
async def get_sessions_endpoint():
    sessions = await list_all_sessions()
    if not sessions:
        await create_session()
        sessions = await list_all_sessions()
    return sessions


@app.post("/api/sessions/new")
async def create_session_endpoint(req: Optional[NewSessionRequest] = Body(default=None)):
    title = req.title if req else "Новый диалог"
    cwd = req.cwd if req else None
    mode = req.mode if req else "plan"
    session = await create_session(title=title, cwd=cwd, mode=mode)
    session["tokens"] = calculate_active_tokens(session)
    return session


@app.get("/api/sessions/{session_id}")
async def get_single_session_endpoint(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    session["tokens"] = calculate_active_tokens(session)
    return session


@app.patch("/api/sessions/{session_id}")
async def patch_session_endpoint(session_id: str, req: SessionPatchRequest):
    updates = {}
    if req.title is not None:
        updates["title"] = req.title
    if req.mode is not None:
        updates["mode"] = req.mode
    if req.cwd is not None:
        updates["cwd"] = req.cwd
    try:
        session = await update_session_fields(session_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    session["tokens"] = calculate_active_tokens(session)
    return session


@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    stop_session_execution(session_id)
    await delete_session(session_id)
    return {"status": "deleted"}


@app.post("/api/distill")
async def manual_distill_endpoint(req: ManualDistillRequest):
    session = await get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    st = session_distill_status.get(req.session_id, {})
    if st.get("status") == "running":
        return {"status": "running", "message": "Фоновое сжатие памяти уже выполняется"}

    asyncio.create_task(distill_session_async(req.session_id, fallback_model=req.model))
    return {"status": "started", "message": "Фоновое сжатие памяти запущено параллельно"}


@app.get("/api/distill/status/{session_id}")
async def get_distill_status_endpoint(session_id: str):
    return session_distill_status.get(session_id, {"status": "idle"})


@app.post("/api/chat/stop")
async def stop_chat_endpoint(req: StopRequest):
    stopped = stop_session_execution(req.session_id)
    return {"status": "stopping" if stopped else "idle", "stopped": stopped}


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    user_text = (req.message or "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")

    session = await get_session(req.session_id) if req.session_id else None
    if not session:
        short_title = user_text[:40] + ("..." if len(user_text) > 40 else "")
        session = await create_session(title=short_title, mode=req.mode or "plan")

    session_id = session["id"]
    target_mode = req.mode if req.mode in ("plan", "act") else session["mode"]
    fields_to_update = {}
    if target_mode != session["mode"]:
        fields_to_update["mode"] = target_mode
    if session.get("title") in ("Новый диалог", "Новый диалог (Дистиллятор)", ""):
        fields_to_update["title"] = user_text[:40] + ("..." if len(user_text) > 40 else "")
    if fields_to_update:
        session = await update_session_fields(session_id, **fields_to_update) or session

    await append_session_message(session_id, {"role": "user", "content": user_text})

    safe_limit = max(4096, min(1_000_000, int(req.context_limit or 32000)))
    safe_thresh = max(0.20, min(0.95, float(req.compress_threshold or 0.50)))

    return StreamingResponse(
        chat_stream_generator(
            session_id=session_id,
            user_text=user_text,
            model=req.model,
            reasoning_effort=req.reasoning_effort,
            context_limit=safe_limit,
            compress_threshold=safe_thresh,
            mode=target_mode,
            approve_execution=req.approve_execution,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    cfg = load_config()
    port = cfg["port"]
    print(f"🚀 Запуск NanoAgent v2.0 (Context Distiller) на http://localhost:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

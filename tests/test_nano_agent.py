import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import core.config as cfg_mod
import core.context as ctx_mod
import core.storage as storage_mod
import core.tools as tools_mod


class TestNanoAgentV2(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="nano_test_"))
        self.orig_env_file = cfg_mod.ENV_FILE
        self.orig_prompt_file = cfg_mod.SYSTEM_PROMPT_FILE
        self.orig_sessions_dir = storage_mod.SESSIONS_DIR
        self.orig_workspace = tools_mod._WORKSPACE_HOST
        self.orig_environ = os.environ.copy()

        cfg_mod.ENV_FILE = self.tmp_dir / ".env"
        cfg_mod.SYSTEM_PROMPT_FILE = self.tmp_dir / "system_prompt.txt"
        storage_mod.SESSIONS_DIR = self.tmp_dir / "sessions"
        storage_mod.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        tools_mod._WORKSPACE_HOST = self.tmp_dir.resolve()
        for k in ("BASE_URL", "ABLIT_KEY", "OPENROUTER_API_KEY", "ADMIN_KEY", "PORT"):
            os.environ.pop(k, None)
        cfg_mod.invalidate_balance_cache()

    def tearDown(self) -> None:
        cfg_mod.ENV_FILE = self.orig_env_file
        cfg_mod.SYSTEM_PROMPT_FILE = self.orig_prompt_file
        storage_mod.SESSIONS_DIR = self.orig_sessions_dir
        tools_mod._WORKSPACE_HOST = self.orig_workspace
        os.environ.clear()
        os.environ.update(self.orig_environ)
        cfg_mod.invalidate_balance_cache()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_no_hardcoded_secrets_and_placeholder_rejection(self) -> None:
        for py_path in [PROJECT_ROOT / "server.py", *list((PROJECT_ROOT / "core").glob("*.py"))]:
            src = py_path.read_text(encoding="utf-8")
            self.assertNotRegex(src, r"ak_[A-Za-z0-9_-]{15,}", f"Secret pattern found in {py_path}")
            self.assertNotRegex(src, r"sk_[A-Za-z0-9_-]{15,}", f"Secret pattern found in {py_path}")
            self.assertNotRegex(src, r"sk-or-v1-[A-Za-z0-9]{15,}", f"Secret pattern found in {py_path}")

        cfg_mod.ENV_FILE.write_text(
            "BASE_URL=https://api.abliteration.ai/v1\n"
            "ABLIT_KEY=your_abliteration_api_key_here\n"
            "ADMIN_KEY=sk_...\n"
            "PORT=5051\n",
            encoding="utf-8",
        )
        loaded = cfg_mod.load_config()
        self.assertFalse(loaded["has_key"])
        self.assertFalse(loaded["has_admin_key"])

    def test_partial_config_update_preserves_existing_key(self) -> None:
        saved1 = cfg_mod.save_config(
            provider="abliteration",
            api_key="ak_dummy_key1",
            admin_key="sk_dummy_adm1",
        )
        self.assertTrue(saved1["has_key"])
        self.assertTrue(saved1["has_admin_key"])

        # Update provider/url without passing api_key -> keeps existing key
        saved2 = cfg_mod.save_config(
            provider="custom",
            api_key="",
            base_url="http://127.0.0.1:8080/v1",
            admin_key="__CLEAR__",
        )
        self.assertEqual(saved2["provider"], "custom")
        self.assertEqual(saved2["base_url"], "http://127.0.0.1:8080/v1")
        self.assertEqual(saved2["api_key"], "ak_dummy_key1")
        self.assertFalse(saved2["has_admin_key"])

    async def test_session_migration_and_atomic_distill_commit(self) -> None:
        real_sample = PROJECT_ROOT / "data" / "sessions" / "a343cad4.json"
        if real_sample.exists():
            shutil.copy2(real_sample, storage_mod.SESSIONS_DIR / "a343cad4.json")
            migrated = await storage_mod.get_session("a343cad4")
            self.assertIsNotNone(migrated)
            self.assertTrue(bool(migrated["active_memory"]))
            self.assertTrue(all("msg_id" in m for m in migrated["messages"]))

        s = await storage_mod.create_session(title="Race Test", cwd=str(self.tmp_dir), mode="plan")
        sid = s["id"]
        await storage_mod.append_session_message(sid, {"role": "user", "content": "шаг 1"})
        await storage_mod.append_session_message(sid, {"role": "assistant", "content": "ответ 1"})
        snap = await storage_mod.get_session(sid)
        old_ids = {m["msg_id"] for m in snap["messages"]}

        # Simulate agent appending new message concurrently before distill finishes
        await storage_mod.append_session_message(sid, {"role": "user", "content": "параллельное сообщение"})

        res = await storage_mod.commit_distillation(
            session_id=sid,
            compressed_ids=old_ids,
            new_memory="### 🎯 Целевая задача пользователя:\nТест",
            tokens_before=500,
        )
        self.assertIsNotNone(res)

        final_s = await storage_mod.get_session(sid)
        contents = [m.get("content") for m in final_s["messages"]]
        self.assertIn("параллельное сообщение", contents)
        self.assertEqual(final_s["active_memory"], "### 🎯 Целевая задача пользователя:\nТест")
        # Old messages are marked compressed, new user message stays uncompressed
        par_msg = next(m for m in final_s["messages"] if m.get("content") == "параллельное сообщение")
        self.assertFalse(par_msg["compressed"])
        old_msg = next(m for m in final_s["messages"] if m.get("content") == "шаг 1")
        self.assertTrue(old_msg["compressed"])

    def test_build_safe_api_messages_repairs_tools_and_enforces_limit(self) -> None:
        broken_session = {
            "active_memory": "",
            "messages": [
                {"role": "tool", "tool_call_id": "orphan_0", "content": "orphan output"},
                {"role": "user", "content": "Первый запрос"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "type": "function", "function": {"name": "bash", "arguments": "{\"command\":\"ls\"}"}},
                        {"id": "call_2", "type": "function", "function": {"name": "bash", "arguments": "{\"command\":\"pwd\"}"}},
                    ],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "fileA\nfileB"},
                # Intentionally missing call_2!
                {"role": "user", "content": "Второй запрос"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call_3", "type": "function", "function": {"name": "bash", "arguments": "{\"command\":\"cat big\"}"}},
                    ],
                },
                {"role": "tool", "tool_call_id": "call_3", "content": "X" * 20000},
            ],
        }

        limit = 1800
        built = ctx_mod.build_safe_api_messages(broken_session, "System prompt", limit)

        # Must never contain orphan_0
        self.assertFalse(any(m.get("tool_call_id") == "orphan_0" for m in built))
        # Every tool_call_id present in tool messages must have a preceding assistant.tool_calls
        seen_tc_ids = set()
        for m in built:
            if m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    seen_tc_ids.add(tc["id"])
            elif m["role"] == "tool":
                self.assertIn(m["tool_call_id"], seen_tc_ids)

        # Also check repair on an isolated broken tail without overflow
        small_built = ctx_mod.build_safe_api_messages(
            {
                "active_memory": "",
                "messages": broken_session["messages"][:4],
            },
            "System prompt",
            32000,
        )
        tool_ids = [m["tool_call_id"] for m in small_built if m["role"] == "tool"]
        self.assertEqual(tool_ids, ["call_1", "call_2"])
        missing_reply = [m for m in small_built if m.get("tool_call_id") == "call_2"][0]
        self.assertIn("прервано", missing_reply["content"])

        # Token count of built messages must be strictly <= limit
        total_toks = sum(ctx_mod._msg_tokens(m) for m in built)
        self.assertLessEqual(total_toks, limit)

    async def test_fastapi_endpoints_smoke(self) -> None:
        import httpx
        import server as srv_mod

        cfg_mod.save_config(provider="abliteration", api_key="ak_dummy_api1")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=srv_mod.app),
            base_url="http://testserver",
        ) as ac:
            r_idx = await ac.get("/")
            self.assertEqual(r_idx.status_code, 200)
            self.assertIn("NanoAgent", r_idx.text)
            self.assertIn("styles.css?v=", r_idx.text)

            r_st = await ac.get("/api/status")
            self.assertEqual(r_st.status_code, 200)
            self.assertTrue(r_st.json()["has_key"])
            self.assertEqual(r_st.json()["distill_engine"], "gemini_free")
            self.assertIn("keys_pool", r_st.json())

            # Test Key Pool API endpoints
            r_keys = await ac.get("/api/keys")
            self.assertEqual(r_keys.status_code, 200)
            self.assertIn("pairs", r_keys.json())

            # Add second pair
            r_add = await ac.post("/api/keys", json={
                "api_key": "ak_dummy_pair2",
                "admin_key": "sk_dummy_adm2",
                "label": "Тестовый Аккаунт 2",
            })
            self.assertEqual(r_add.status_code, 200)
            pair2_id = r_add.json()["pair"]["id"]

            # Switch active pair
            r_act = await ac.post(f"/api/keys/{pair2_id}/activate")
            self.assertEqual(r_act.status_code, 200)
            self.assertEqual(r_act.json()["pool"]["active_pair_id"], pair2_id)

            # Update settings
            r_set = await ac.patch("/api/keys/settings", json={"auto_rotate": True, "auto_purge_exhausted": True})
            self.assertEqual(r_set.status_code, 200)
            self.assertTrue(r_set.json()["pool"]["auto_rotate"])

            # Delete pair
            r_del_k = await ac.delete(f"/api/keys/{pair2_id}")
            self.assertEqual(r_del_k.status_code, 200)

            r_new = await ac.post("/api/sessions/new", json={"title": "API Test", "mode": "plan"})
            self.assertEqual(r_new.status_code, 200)
            sid = r_new.json()["id"]

            r_patch = await ac.patch(f"/api/sessions/{sid}", json={"mode": "act", "title": "Renamed"})
            self.assertEqual(r_patch.status_code, 200)
            self.assertEqual(r_patch.json()["mode"], "act")
            self.assertEqual(r_patch.json()["title"], "Renamed")

            r_stop = await ac.post("/api/chat/stop", json={"session_id": sid})
            self.assertEqual(r_stop.status_code, 200)

            r_pr = await ac.post("/api/system-prompt", json={"content": "Custom instruction"})
            self.assertEqual(r_pr.status_code, 200)
            r_pr_rst = await ac.post("/api/system-prompt/reset")
            self.assertEqual(r_pr_rst.status_code, 200)

            r_del = await ac.delete(f"/api/sessions/{sid}")
            self.assertEqual(r_del.status_code, 200)

    async def test_gemini_free_wallet_guard_and_agy_distill_success(self) -> None:
        from unittest.mock import AsyncMock, patch

        cfg_mod.save_config(
            provider="abliteration",
            api_key="ak_dummy_api1",
            distill_engine="gemini_free",
        )
        s = await storage_mod.create_session(title="Wallet Guard Test", cwd=str(self.tmp_dir))
        sid = s["id"]
        await storage_mod.append_session_message(sid, {"role": "user", "content": "первый вопрос о сервере"})
        await storage_mod.append_session_message(sid, {"role": "assistant", "content": "первый ответ про порт 5051"})
        await storage_mod.append_session_message(sid, {"role": "user", "content": "второй вопрос"})

        # Case 1: agy fails / unavailable -> paid client MUST NOT be called!
        with patch.object(ctx_mod, "load_config", return_value={
            **cfg_mod.load_config(),
            "distill_engine": "gemini_free",
            "agy_available": False,
            "has_gemini_key": False,
        }), patch.object(ctx_mod, "_run_paid_main_api_distiller", new=AsyncMock()) as paid_mock:
            await ctx_mod.distill_session_async(sid, fallback_model="abliterated-model-large-flash", manual=True)
            paid_mock.assert_not_awaited()
            st_err = ctx_mod.session_distill_status[sid]
            self.assertEqual(st_err["status"], "error")
            self.assertIn("$0", st_err["error"])

        # Case 2: agy raises RuntimeError -> paid client STILL MUST NOT be called!
        with patch.object(ctx_mod, "load_config", return_value={
            **cfg_mod.load_config(),
            "distill_engine": "gemini_free",
            "agy_available": True,
            "has_gemini_key": False,
        }), patch.object(
            ctx_mod, "run_agy_gemini_distiller", new=AsyncMock(side_effect=RuntimeError("cli timeout"))
        ), patch.object(ctx_mod, "_run_paid_main_api_distiller", new=AsyncMock()) as paid_mock2:
            await ctx_mod.distill_session_async(sid, fallback_model="abliterated-model-large-flash", manual=True)
            paid_mock2.assert_not_awaited()
            self.assertEqual(ctx_mod.session_distill_status[sid]["status"], "error")
            self.assertIn("$0", ctx_mod.session_distill_status[sid]["error"])

        # Case 3: successful agy run saves engine_label = "Gemini 3.8 Flash · $0"
        fake_summary = "### Целевая задача пользователя\nПроверка бесплатного сжатия."
        with patch.object(ctx_mod, "load_config", return_value={
            **cfg_mod.load_config(),
            "distill_engine": "gemini_free",
            "agy_available": True,
            "has_gemini_key": False,
        }), patch.object(
            ctx_mod, "run_agy_gemini_distiller", new=AsyncMock(return_value=fake_summary)
        ), patch.object(ctx_mod, "_run_paid_main_api_distiller", new=AsyncMock()) as paid_mock3:
            await ctx_mod.distill_session_async(sid, manual=True)
            paid_mock3.assert_not_awaited()

        st_ok = ctx_mod.session_distill_status[sid]
        self.assertEqual(st_ok["status"], "done")
        self.assertEqual(st_ok["engine_label"], "Gemini 3.8 Flash · $0")
        loaded = await storage_mod.get_session(sid)
        self.assertEqual(loaded["active_memory"], fake_summary)
        distill_ev = [m for m in loaded["messages"] if m.get("event") == "distilled"]
        self.assertEqual(len(distill_ev), 1)
        self.assertEqual(distill_ev[0]["engine_label"], "Gemini 3.8 Flash · $0")

    async def test_all_six_tools_and_cancellation_and_plan_gate(self) -> None:
        # 1. Plan mode gating
        self.assertFalse(tools_mod.is_execution_approved("Расскажи как устроен сервер?", False))
        self.assertFalse(tools_mod.is_execution_approved("Пока не делай ничего", False))
        self.assertTrue(tools_mod.is_execution_approved("делай", False))
        self.assertTrue(tools_mod.is_execution_approved("Приступай к выполнению", False))

        blocked = await tools_mod.execute_tool("bash", {"command": "echo hi"}, str(self.tmp_dir), allow_mutating=False)
        self.assertEqual(blocked["exit_code"], 1)
        self.assertIn("заблокировано", blocked["output"])

        # 2. write_file + read_file + edit_file
        w_res = await tools_mod.execute_tool(
            "write_file",
            {"path": "sub/demo.py", "content": "def hello():\n    return 'world'\n"},
            str(self.tmp_dir),
        )
        self.assertEqual(w_res["exit_code"], 0)
        self.assertTrue((self.tmp_dir / "sub" / "demo.py").exists())

        r_res = await tools_mod.execute_tool(
            "read_file",
            {"path": "sub/demo.py", "start_line": 1, "end_line": 10},
            str(self.tmp_dir),
        )
        self.assertEqual(r_res["exit_code"], 0)
        self.assertIn("1 | def hello():", r_res["output"])

        e_res = await tools_mod.execute_tool(
            "edit_file",
            {"path": "sub/demo.py", "old_text": "return 'world'", "new_text": "return 'nano'"},
            str(self.tmp_dir),
        )
        self.assertEqual(e_res["exit_code"], 0)
        self.assertIn("-    return 'world'", e_res["diff"])
        self.assertIn("+    return 'nano'", e_res["diff"])

        # 3. list_dir + search_files (create ignored __pycache__ to ensure skipped)
        (self.tmp_dir / "__pycache__").mkdir()
        (self.tmp_dir / "__pycache__" / "junk.pyc").write_bytes(b"\x00\x01")
        l_res = await tools_mod.execute_tool("list_dir", {"path": ".", "max_depth": 3}, str(self.tmp_dir))
        self.assertIn("demo.py", l_res["output"])
        self.assertNotIn("__pycache__", l_res["output"])

        s_res = await tools_mod.execute_tool("search_files", {"pattern": "return 'nano'", "path": "."}, str(self.tmp_dir))
        self.assertEqual(s_res["exit_code"], 0)
        self.assertIn("demo.py", s_res["output"])

        # 4. bash: persistent cd detection & large output truncation
        b_cd = await tools_mod.execute_tool("bash", {"command": "cd sub && pwd"}, str(self.tmp_dir))
        self.assertEqual(b_cd["exit_code"], 0)
        self.assertEqual(b_cd["new_cwd"], str((self.tmp_dir / "sub").resolve()))

        b_big = await tools_mod.execute_tool(
            "bash",
            {"command": "python3 -c \"print('A' * 22000)\""},
            str(self.tmp_dir),
        )
        self.assertEqual(b_big["exit_code"], 0)
        self.assertIn("вывод обрезан", b_big["output"])
        self.assertLess(len(b_big["output"]), 15500)

        # 5. bash cancellation via cancel_event
        ev = asyncio.Event()
        async def trigger_cancel():
            await asyncio.sleep(0.25)
            ev.set()

        t0 = time.monotonic()
        canceller = asyncio.create_task(trigger_cancel())
        b_cancel = await tools_mod.execute_tool(
            "bash",
            {"command": "sleep 30"},
            str(self.tmp_dir),
            cancel_event=ev,
        )
        await canceller
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 3.0)
        self.assertEqual(b_cancel["exit_code"], -1)
        self.assertIn("остановлено", b_cancel["output"])

    async def test_bwrap_sandbox_isolation(self) -> None:
        if not tools_mod._BWRAP_ENABLED:
            self.skipTest("bwrap not enabled")

        # 1. /home is hidden inside bash
        res_home = await tools_mod.execute_tool("bash", {"command": "ls -A /home"}, str(self.tmp_dir))
        self.assertEqual(res_home["exit_code"], 0)
        self.assertEqual(res_home["output"].strip(), "[пустой вывод / success]")

        # 2. /etc is read-only inside bash
        res_ro = await tools_mod.execute_tool("bash", {"command": "touch /etc/bwrap_probe 2>&1"}, str(self.tmp_dir))
        self.assertNotEqual(res_ro["exit_code"], 0)

        # 3. Python file tools block /home and writes outside workspace
        r_home = await tools_mod.execute_tool("read_file", {"path": "/home"}, str(self.tmp_dir))
        self.assertEqual(r_home["exit_code"], 1)
        self.assertIn("sandbox", r_home["output"])

        w_out = await tools_mod.execute_tool(
            "write_file",
            {"path": "/var/tmp/outside_sandbox.txt", "content": "x"},
            str(self.tmp_dir),
        )
        self.assertEqual(w_out["exit_code"], 1)
        self.assertIn("sandbox", w_out["output"])


if __name__ == "__main__":
    unittest.main()

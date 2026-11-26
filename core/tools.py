import asyncio
import difflib
import fnmatch
import os
import re
import shutil
import signal
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

READ_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file with line numbers. Supports line ranges for large files.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to cwd or absolute)"},
                "start_line": {"type": "integer", "description": "1-based start line (default 1)"},
                "end_line": {"type": "integer", "description": "1-based inclusive end line (default 250)"},
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Create or overwrite a UTF-8 text file safely without shell escaping. Creates parent directories automatically.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to cwd or absolute)"},
                "content": {"type": "string", "description": "Complete text content to write"},
            },
            "required": ["path", "content"],
        },
    },
}

EDIT_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Replace an exact substring in a file and return a unified diff.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to cwd or absolute)"},
                "old_text": {"type": "string", "description": "Exact existing text to replace"},
                "new_text": {"type": "string", "description": "Replacement text"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences instead of requiring unique match"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
}

LIST_DIR_TOOL = {
    "type": "function",
    "function": {
        "name": "list_dir",
        "description": "List directory tree with sizes, skipping noisy folders (.git, node_modules, __pycache__, venv).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default '.')"},
                "max_depth": {"type": "integer", "description": "Traversal depth 1..5 (default 2)"},
            },
            "required": [],
        },
    },
}

SEARCH_FILES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Search for a regex or text pattern across files in a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern or plain text to search"},
                "path": {"type": "string", "description": "Directory or file path to search in (default '.')"},
                "file_glob": {"type": "string", "description": "Optional filename glob filter, e.g. '*.py'"},
            },
            "required": ["pattern"],
        },
    },
}

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Execute a shell command (bash on Linux/macOS, PowerShell on Windows). Tracks cd directory changes across calls.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Exact shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 120, max 600)"},
            },
            "required": ["command"],
        },
    },
}

READ_ONLY_TOOLS = [READ_FILE_TOOL, LIST_DIR_TOOL, SEARCH_FILES_TOOL]
ALL_TOOLS = [
    BASH_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    EDIT_FILE_TOOL,
    LIST_DIR_TOOL,
    SEARCH_FILES_TOOL,
]
MUTATING_TOOL_NAMES = {"bash", "write_file", "edit_file"}

_IGNORED_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv"}
MAX_TOOL_OUTPUT_CHARS = 16000


_NEGATION_RE = re.compile(
    r"\b(не\s+(?:делай|выполняй|выполни|запускай|запусти|трогай|меняй)|только\s+план|без\s+выполнения)\b",
    re.IGNORECASE,
)
_DIRECT_EXEC_RE = re.compile(
    r"(?<![а-яёa-z0-9_])("
    r"делай|сделай|выполняй|выполни|приступай|запускай|запусти|действуй|"
    r"погнали|поехали|продолжай\s+выполнение|проверь\s+в\s+терминале|выполни\s+план"
    r")(?![а-яёa-z0-9_])",
    re.IGNORECASE,
)
_SHORT_ACK_RE = re.compile(
    r"^(?:ну\s+)?(да|ок|окей|ok|okay|давай|хорошо|ладно|можно|подтверждаю|согласен|утверждаю|го|впер[её]д)(?:[\s,!.]*(?:делай|выполняй|приступай|запускай))?[!.?]*$",
    re.IGNORECASE,
)


def is_execution_approved(user_text: str, explicit_flag: bool = False) -> bool:
    if explicit_flag:
        return True
    txt = (user_text or "").strip()
    if not txt:
        return False
    if _NEGATION_RE.search(txt):
        return False
    if _SHORT_ACK_RE.match(txt):
        return True
    if _DIRECT_EXEC_RE.search(txt) and not txt.endswith("?"):
        return True
    return False


def _resolve_path(raw_path: Optional[str], session_cwd: str) -> Path:
    base = Path(session_cwd) if session_cwd else Path.cwd()
    raw = (raw_path or ".").strip() or "."
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def _truncate_large_output(output: str) -> str:
    if len(output) <= MAX_TOOL_OUTPUT_CHARS:
        return output
    log_path = Path(tempfile.gettempdir()) / f"nanoagent_out_{uuid.uuid4().hex[:8]}.log"
    try:
        log_path.write_text(output, encoding="utf-8", errors="replace")
        log_hint = f"полный лог сохранён в {log_path}"
    except Exception:
        log_hint = "не удалось сохранить полный лог на диск"
    head = output[:8000]
    tail = output[-6000:]
    return (
        f"{head}\n\n"
        f"... [вывод обрезан: всего {len(output)} симв., показано начало (8000) и конец (6000); {log_hint}] ...\n\n"
        f"{tail}"
    )


def _tool_read_file(args: Dict[str, Any], session_cwd: str) -> dict:
    raw_path = args.get("path", "")
    if not raw_path:
        return {"output": "[ошибка: не указан параметр path]", "exit_code": 1}
    p = _resolve_path(raw_path, session_cwd)
    if not p.exists():
        return {"output": f"[ошибка: файл не найден: {p}]", "exit_code": 1}
    if not p.is_file():
        return {"output": f"[ошибка: это директория, используйте list_dir: {p}]", "exit_code": 1}

    try:
        raw_bytes = p.read_bytes()
        if b"\x00" in raw_bytes[:4096]:
            return {"output": f"[ошибка: файл {p} является бинарным ({_format_size(len(raw_bytes))})]", "exit_code": 1}
        text = raw_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        return {"output": f"[ошибка чтения {p}: {e}]", "exit_code": 1}

    lines = text.splitlines()
    total = len(lines)
    start_line = max(1, int(args.get("start_line") or 1))
    default_end = start_line + 249
    end_line = int(args.get("end_line") or default_end)
    if end_line < start_line:
        end_line = start_line
    if end_line - start_line + 1 > 500:
        end_line = start_line + 499

    if total == 0:
        return {"output": f"Файл: {p} (пустой, 0 строк)", "exit_code": 0}
    if start_line > total:
        return {"output": f"Файл: {p} содержит всего {total} строк (запрошено с {start_line}).", "exit_code": 0}

    slice_end = min(total, end_line)
    numbered = [f"{i:>5} | {lines[i - 1]}" for i in range(start_line, slice_end + 1)]
    header = f"Файл: {p} (строки {start_line}-{slice_end} из {total}, {_format_size(len(raw_bytes))})"
    footer = ""
    if slice_end < total:
        footer = f"\n... [показаны строки {start_line}-{slice_end} из {total}; для продолжения вызовите read_file(start_line={slice_end + 1})] ..."

    return {"output": _truncate_large_output(header + "\n" + "\n".join(numbered) + footer), "exit_code": 0}


def _tool_write_file(args: Dict[str, Any], session_cwd: str) -> dict:
    raw_path = args.get("path", "")
    content = args.get("content")
    if not raw_path:
        return {"output": "[ошибка: не указан параметр path]", "exit_code": 1}
    if content is None:
        return {"output": "[ошибка: не указан параметр content]", "exit_code": 1}

    p = _resolve_path(raw_path, session_cwd)
    old_text: Optional[str] = None
    if p.exists() and p.is_file() and p.stat().st_size < 512_000:
        try:
            raw = p.read_bytes()
            if b"\x00" not in raw[:4096]:
                old_text = raw.decode("utf-8", errors="replace")
        except Exception:
            old_text = None

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except Exception as e:
        return {"output": f"[ошибка записи {p}: {e}]", "exit_code": 1}

    diff_text: Optional[str] = None
    if old_text is not None and old_text != content:
        diff_lines = list(
            difflib.unified_diff(
                old_text.splitlines(),
                content.splitlines(),
                fromfile=f"a/{p.name}",
                tofile=f"b/{p.name}",
                lineterm="",
                n=3,
            )
        )
        if diff_lines:
            if len(diff_lines) > 120:
                diff_lines = diff_lines[:120] + [f"... [diff обрезан, всего {len(diff_lines)} строк]"]
            diff_text = "\n".join(diff_lines)

    line_count = len(content.splitlines())
    byte_count = len(content.encode("utf-8"))
    action = "перезаписан" if old_text is not None else "создан"
    return {
        "output": f"Файл {action}: {p} ({line_count} строк, {byte_count} байт)",
        "diff": diff_text,
        "exit_code": 0,
    }


def _tool_edit_file(args: Dict[str, Any], session_cwd: str) -> dict:
    raw_path = args.get("path", "")
    old_text = args.get("old_text")
    new_text = args.get("new_text")
    replace_all = bool(args.get("replace_all", False))

    if not raw_path:
        return {"output": "[ошибка: не указан параметр path]", "exit_code": 1}
    if old_text is None or new_text is None:
        return {"output": "[ошибка: требуются параметры old_text и new_text]", "exit_code": 1}
    if old_text == "":
        return {"output": "[ошибка: old_text не может быть пустым]", "exit_code": 1}

    p = _resolve_path(raw_path, session_cwd)
    if not p.exists() or not p.is_file():
        return {"output": f"[ошибка: файл не найден: {p}]", "exit_code": 1}

    try:
        raw = p.read_bytes()
        if b"\x00" in raw[:4096]:
            return {"output": f"[ошибка: бинарный файл нельзя редактировать через edit_file: {p}]", "exit_code": 1}
        current = raw.decode("utf-8", errors="replace")
    except Exception as e:
        return {"output": f"[ошибка чтения {p}: {e}]", "exit_code": 1}

    occurrences = current.count(old_text)
    if occurrences == 0:
        return {
            "output": f"[ошибка: фрагмент old_text не найден в {p}. Проверьте отступы и пробелы через read_file.]",
            "exit_code": 1,
        }
    if occurrences > 1 and not replace_all:
        return {
            "output": (
                f"[ошибка: найдено {occurrences} вхождений old_text в {p}. "
                f"Добавьте больше контекста или передайте replace_all=true.]"
            ),
            "exit_code": 1,
        }

    updated = current.replace(old_text, new_text) if replace_all else current.replace(old_text, new_text, 1)
    try:
        p.write_text(updated, encoding="utf-8")
    except Exception as e:
        return {"output": f"[ошибка сохранения {p}: {e}]", "exit_code": 1}

    diff_lines = list(
        difflib.unified_diff(
            current.splitlines(),
            updated.splitlines(),
            fromfile=f"a/{p.name}",
            tofile=f"b/{p.name}",
            lineterm="",
            n=3,
        )
    )
    if len(diff_lines) > 120:
        diff_lines = diff_lines[:120] + [f"... [diff обрезан, всего {len(diff_lines)} строк]"]
    diff_text = "\n".join(diff_lines) if diff_lines else "(без текстовых изменений)"

    return {
        "output": f"Обновлён {p} (замен: {occurrences if replace_all else 1})\n\n{diff_text}",
        "diff": diff_text,
        "exit_code": 0,
    }


def _tool_list_dir(args: Dict[str, Any], session_cwd: str) -> dict:
    p = _resolve_path(args.get("path", "."), session_cwd)
    max_depth = max(1, min(5, int(args.get("max_depth") or 2)))

    if not p.exists():
        return {"output": f"[ошибка: путь не существует: {p}]", "exit_code": 1}
    if not p.is_dir():
        return {"output": f"[ошибка: путь не является директорией: {p}]", "exit_code": 1}

    entries: List[str] = [f"Содержимое {p} (глубина <= {max_depth}):"]
    count = 0
    truncated = False

    def walk(dir_path: Path, depth: int, prefix: str) -> None:
        nonlocal count, truncated
        if depth > max_depth or truncated:
            return
        try:
            children = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            entries.append(f"{prefix}[нет доступа]")
            return

        for child in children:
            if count >= 250:
                truncated = True
                return
            name = child.name
            if child.is_dir() and name in _IGNORED_DIRS:
                continue
            count += 1
            if child.is_dir():
                entries.append(f"{prefix}{name}/")
                if depth < max_depth:
                    walk(child, depth + 1, prefix + "  ")
            else:
                try:
                    sz = _format_size(child.stat().st_size)
                except OSError:
                    sz = "?"
                entries.append(f"{prefix}{name} ({sz})")

    walk(p, 1, "  ")
    if truncated:
        entries.append("... [показаны первые 250 элементов]")
    elif count == 0:
        entries.append("  [директория пуста]")

    return {"output": "\n".join(entries), "exit_code": 0}


async def _kill_process_tree(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=5,
            )
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


async def _wait_proc_with_cancel(
    proc: asyncio.subprocess.Process,
    timeout: int,
    cancel_event: Optional[asyncio.Event],
) -> Tuple[bytes, bytes, bool, bool]:
    comm_task = asyncio.create_task(proc.communicate())
    cancel_task = asyncio.create_task(cancel_event.wait()) if cancel_event else None

    wait_set = {comm_task}
    if cancel_task:
        wait_set.add(cancel_task)

    done, pending = await asyncio.wait(
        wait_set,
        timeout=timeout,
        return_when=asyncio.FIRST_COMPLETED,
    )

    cancelled = False
    timed_out = False

    if cancel_task and cancel_task in done:
        cancelled = True
        await _kill_process_tree(proc)
    elif comm_task not in done:
        timed_out = True
        await _kill_process_tree(proc)

    if cancel_task and not cancel_task.done():
        cancel_task.cancel()
        try:
            await cancel_task
        except asyncio.CancelledError:
            pass

    if not comm_task.done():
        try:
            stdout_b, stderr_b = await asyncio.wait_for(comm_task, timeout=3.0)
        except Exception:
            comm_task.cancel()
            stdout_b, stderr_b = b"", b""
    else:
        stdout_b, stderr_b = await comm_task

    return stdout_b, stderr_b, cancelled, timed_out


async def _tool_search_files(
    args: Dict[str, Any],
    session_cwd: str,
    cancel_event: Optional[asyncio.Event],
) -> dict:
    pattern = args.get("pattern", "")
    if not pattern:
        return {"output": "[ошибка: не указан параметр pattern]", "exit_code": 1}

    target = _resolve_path(args.get("path", "."), session_cwd)
    if not target.exists():
        return {"output": f"[ошибка: путь не существует: {target}]", "exit_code": 1}

    file_glob = (args.get("file_glob") or "").strip()
    rg_bin = shutil.which("rg")

    if rg_bin:
        cmd = [
            rg_bin,
            "-n",
            "--no-heading",
            "--color",
            "never",
            "--max-count",
            "30",
            "--glob",
            "!.git/**",
            "--glob",
            "!node_modules/**",
            "--glob",
            "!__pycache__/**",
            "--glob",
            "!venv/**",
            "--glob",
            "!.venv/**",
        ]
        if file_glob:
            cmd.extend(["--glob", file_glob])
        cmd.extend(["-e", pattern, str(target)])

        kwargs: Dict[str, Any] = {
            "stdin": asyncio.subprocess.DEVNULL,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
        }
        if os.name != "nt":
            kwargs["start_new_session"] = True

        proc = await asyncio.create_subprocess_exec(*cmd, **kwargs)
        stdout_b, stderr_b, cancelled, timed_out = await _wait_proc_with_cancel(proc, 30, cancel_event)
        if cancelled:
            return {"output": "[поиск остановлен пользователем]", "exit_code": -1}
        if timed_out:
            return {"output": "[ошибка: таймаут поиска (30 сек)]", "exit_code": -124}

        out = stdout_b.decode("utf-8", errors="replace").strip()
        err = stderr_b.decode("utf-8", errors="replace").strip()
        if proc.returncode == 1 or not out:
            if proc.returncode not in (0, 1) and err:
                return {"output": f"[ошибка поиска]: {err}", "exit_code": proc.returncode}
            return {"output": f"Совпадений по '{pattern}' в {target} не найдено.", "exit_code": 0}

        lines = out.splitlines()
        truncated = ""
        if len(lines) > 100:
            lines = lines[:100]
            truncated = f"\n... [показаны первые 100 совпадений из {len(out.splitlines())}]"
        return {"output": _truncate_large_output("\n".join(lines) + truncated), "exit_code": 0}

    # Pure Python fallback
    try:
        regex = re.compile(pattern)
    except re.error:
        regex = re.compile(re.escape(pattern))

    matches: List[str] = []
    if target.is_file():
        files_iter = [target]
    else:
        def _iter_files():
            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in _IGNORED_DIRS]
                for fname in sorted(files):
                    if file_glob and not fnmatch.fnmatch(fname, file_glob):
                        continue
                    yield Path(root) / fname

        files_iter = _iter_files()

    for fp in files_iter:
        if cancel_event and cancel_event.is_set():
            return {"output": "[поиск остановлен пользователем]", "exit_code": -1}
        try:
            if fp.stat().st_size > 2_000_000:
                continue
            raw = fp.read_bytes()
            if b"\x00" in raw[:2048]:
                continue
            txt = raw.decode("utf-8", errors="replace")
            for idx, line in enumerate(txt.splitlines(), 1):
                if regex.search(line):
                    try:
                        rel = str(fp.relative_to(target)) if target.is_dir() else str(fp)
                    except ValueError:
                        rel = str(fp)
                    matches.append(f"{rel}:{idx}:{line[:240]}")
                    if len(matches) >= 100:
                        break
        except Exception:
            continue
        if len(matches) >= 100:
            break

    if not matches:
        return {"output": f"Совпадений по '{pattern}' в {target} не найдено.", "exit_code": 0}
    suffix = "\n... [достигнут лимит в 100 совпадений]" if len(matches) >= 100 else ""
    return {"output": _truncate_large_output("\n".join(matches) + suffix), "exit_code": 0}


async def _tool_bash(
    args: Dict[str, Any],
    session_cwd: str,
    cancel_event: Optional[asyncio.Event],
) -> dict:
    cmd = args.get("command", "")
    if not cmd or not str(cmd).strip():
        return {"output": "[ошибка: пустая команда]", "exit_code": 1}

    try:
        timeout = max(5, min(600, int(args.get("timeout") or 120)))
    except Exception:
        timeout = 120

    cwd_path = session_cwd if (session_cwd and Path(session_cwd).is_dir()) else os.getcwd()
    cwd_marker = Path(tempfile.gettempdir()) / f"nanoagent_cwd_{uuid.uuid4().hex[:8]}"

    try:
        if os.name == "nt":
            ps_script = (
                f"try {{\n{cmd}\n}} finally {{ "
                f"(Get-Location).Path | Out-File -FilePath '{cwd_marker}' -Encoding utf8 -NoNewline "
                f"}}"
            )
            proc = await asyncio.create_subprocess_exec(
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps_script,
                cwd=cwd_path,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            wrapped = f"trap 'pwd > \"{cwd_marker}\" 2>/dev/null || true' EXIT\n{cmd}"
            executable = "/bin/bash" if os.path.exists("/bin/bash") else None
            proc = await asyncio.create_subprocess_shell(
                wrapped,
                executable=executable,
                cwd=cwd_path,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )

        stdout_b, stderr_b, cancelled, timed_out = await _wait_proc_with_cancel(proc, timeout, cancel_event)

        new_cwd: Optional[str] = None
        if cwd_marker.exists():
            try:
                detected = cwd_marker.read_text(encoding="utf-8", errors="replace").strip().lstrip("\ufeff")
                if detected and Path(detected).is_dir() and detected != cwd_path:
                    new_cwd = detected
            except Exception:
                pass

        if cancelled:
            return {
                "output": "[выполнение остановлено пользователем]",
                "new_cwd": new_cwd,
                "exit_code": -1,
            }
        if timed_out:
            return {
                "output": f"[ошибка: таймаут команды ({timeout} сек)]",
                "new_cwd": new_cwd,
                "exit_code": -124,
            }

        out = stdout_b.decode("utf-8", errors="replace")
        err = stderr_b.decode("utf-8", errors="replace")
        res = out
        if err:
            if res and not res.endswith("\n"):
                res += "\n"
            res += f"[stderr]:\n{err}"
        ec = proc.returncode if proc.returncode is not None else 0
        if ec != 0:
            if res and not res.endswith("\n"):
                res += "\n"
            res += f"[exit code: {ec}]"
        if not res.strip():
            res = "[пустой вывод / success]"
            if new_cwd:
                res = f"[переход в каталог: {new_cwd}]"

        return {
            "output": _truncate_large_output(res),
            "new_cwd": new_cwd,
            "exit_code": ec,
        }
    except Exception as e:
        return {"output": f"[ошибка выполнения: {e}]", "exit_code": 1}
    finally:
        try:
            if cwd_marker.exists():
                cwd_marker.unlink()
        except Exception:
            pass


async def execute_tool(
    name: str,
    args: Dict[str, Any],
    session_cwd: str,
    cancel_event: Optional[asyncio.Event] = None,
    allow_mutating: bool = True,
) -> dict:
    if not allow_mutating and name in MUTATING_TOOL_NAMES:
        return {
            "output": (
                f"[заблокировано в режиме ПЛАНИРОВАНИЯ: инструмент '{name}' недоступен без подтверждения. "
                "Предложите план пользователю и дождитесь одобрения.]"
            ),
            "exit_code": 1,
        }

    if name == "read_file":
        return await asyncio.to_thread(_tool_read_file, args, session_cwd)
    if name == "write_file":
        return await asyncio.to_thread(_tool_write_file, args, session_cwd)
    if name == "edit_file":
        return await asyncio.to_thread(_tool_edit_file, args, session_cwd)
    if name == "list_dir":
        return await asyncio.to_thread(_tool_list_dir, args, session_cwd)
    if name == "search_files":
        return await _tool_search_files(args, session_cwd, cancel_event)
    if name == "bash":
        return await _tool_bash(args, session_cwd, cancel_event)

    return {"output": f"[ошибка: неизвестный инструмент '{name}']", "exit_code": 1}

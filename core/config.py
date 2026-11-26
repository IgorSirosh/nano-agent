import os
import platform
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from dotenv import dotenv_values
from openai import AsyncOpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
SYSTEM_PROMPT_FILE = BASE_DIR / "system_prompt.txt"

DEFAULT_BASE_SYSTEM_PROMPT = (
    "Ты персональный AI-ассистент и старший инженер-разработчик с доступом к локальной системе.\n\n"
    "ПРИНЦИПЫ РАБОТЫ:\n"
    "1. Всегда сначала изучай реальное состояние файлов и проекта с помощью инструментов чтения/поиска, а не угадывай.\n"
    "2. Для чтения, поиска и правки кода используй специализированные инструменты (read_file, edit_file, write_file, list_dir, search_files) "
    "— они точнее и безопаснее, чем bash.\n"
    "3. Перед деструктивными операциями (удаление данных, перезапуск критичных служб, правка системных конфигов) предупреждай пользователя.\n"
    "4. Отвечай грамотно, структурированно и на русском языке. Никогда не выдумывай результаты команд, которых не запускал."
)

_PLACEHOLDER_MARKERS = (
    "your_",
    "placeholder",
    "changeme",
    "example",
    "ak_...",
    "sk_...",
    "sk-or-v1-...",
    "xxx",
)

_balance_cache: Dict[str, object] = {
    "ts": 0.0,
    "val": None,
    "cache_key": "",
}
BALANCE_CACHE_TTL = 15.0


def is_valid_secret(val: Optional[str]) -> bool:
    if not val:
        return False
    s = val.strip()
    if len(s) < 8:
        return False
    low = s.lower()
    if "..." in s:
        return False
    for marker in _PLACEHOLDER_MARKERS:
        if low.startswith(marker) or low == marker:
            return False
    return True


def find_agy_binary() -> Optional[str]:
    found = shutil.which("agy")
    if found and os.access(found, os.X_OK):
        return found
    home = Path.home()
    for candidate in (
        home / ".local" / "bin" / "agy",
        home / ".gemini" / "bin" / "agy",
        Path("/usr/local/bin/agy"),
    ):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _read_raw_env() -> Dict[str, str]:
    values: Dict[str, str] = {}
    if ENV_FILE.exists():
        try:
            parsed = dotenv_values(ENV_FILE)
            for k, v in parsed.items():
                if v is not None:
                    values[k] = v
        except Exception:
            pass
    for key in ("BASE_URL", "ABLIT_KEY", "OPENROUTER_API_KEY", "ADMIN_KEY", "PORT", "DISTILL_ENGINE"):
        if key not in values and key in os.environ:
            values[key] = os.environ[key]
    return values


def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) > 10:
        return f"{secret[:6]}...{secret[-4:]}"
    return "***"


def load_config() -> dict:
    env = _read_raw_env()
    base_url = (env.get("BASE_URL") or "https://api.abliteration.ai/v1").strip()
    or_key_raw = (env.get("OPENROUTER_API_KEY") or "").strip()
    ab_key_raw = (env.get("ABLIT_KEY") or "").strip()
    adm_key_raw = (env.get("ADMIN_KEY") or "").strip()
    gem_key_raw = (env.get("GEMINI_API_KEY") or "").strip()

    or_key = or_key_raw if is_valid_secret(or_key_raw) else ""
    ab_key = ab_key_raw if is_valid_secret(ab_key_raw) else ""
    admin_key = adm_key_raw if is_valid_secret(adm_key_raw) else ""
    gemini_api_key = gem_key_raw if is_valid_secret(gem_key_raw) else ""

    is_openrouter = "openrouter.ai" in base_url.lower() or bool(or_key and not ab_key and or_key.startswith("sk-or-"))
    if is_openrouter:
        provider = "openrouter"
        api_key = or_key or ab_key
    elif "abliteration.ai" in base_url.lower():
        provider = "abliteration"
        api_key = ab_key or or_key
    else:
        provider = "custom"
        api_key = ab_key or or_key

    distill_raw = (env.get("DISTILL_ENGINE") or "gemini_free").strip().lower()
    distill_engine = distill_raw if distill_raw in ("gemini_free", "main_api") else "gemini_free"

    agy_bin = find_agy_binary()
    agy_available = bool(agy_bin)

    if distill_engine == "main_api":
        distill_label = "Основной API (платный)"
    elif agy_available:
        distill_label = "Gemini 3.8 Flash · $0"
    elif gemini_api_key:
        distill_label = "Gemini API Key"
    else:
        distill_label = "Gemini (не найден agy)"

    try:
        port = int(env.get("PORT") or 5051)
    except ValueError:
        port = 5051

    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "admin_key": admin_key,
        "gemini_api_key": gemini_api_key,
        "has_gemini_key": is_valid_secret(gemini_api_key),
        "distill_engine": distill_engine,
        "distill_label": distill_label,
        "agy_available": agy_available,
        "port": port,
        "has_key": is_valid_secret(api_key),
        "has_admin_key": is_valid_secret(admin_key),
        "masked_key": _mask_secret(api_key) if is_valid_secret(api_key) else "",
    }


def save_config(
    provider: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    admin_key: Optional[str] = None,
    distill_engine: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> dict:
    current = load_config()
    prov = (provider or current["provider"] or "abliteration").strip().lower()
    if prov not in ("abliteration", "openrouter", "custom"):
        prov = "abliteration"

    req_key = (api_key or "").strip()
    if req_key:
        if not is_valid_secret(req_key):
            raise ValueError("Указан некорректный или тестовый API-ключ")
        final_key = req_key
    else:
        if not current["has_key"]:
            raise ValueError("API-ключ не может быть пустым")
        final_key = current["api_key"]

    if admin_key == "__CLEAR__":
        final_admin = ""
    elif admin_key is not None and admin_key.strip():
        if not is_valid_secret(admin_key.strip()):
            raise ValueError("Указан некорректный Admin Key")
        final_admin = admin_key.strip()
    else:
        final_admin = current["admin_key"]

    if gemini_api_key == "__CLEAR__":
        final_gemini_key = ""
    elif gemini_api_key is not None and gemini_api_key.strip():
        if not is_valid_secret(gemini_api_key.strip()):
            raise ValueError("Указан некорректный Gemini API Key")
        final_gemini_key = gemini_api_key.strip()
    else:
        final_gemini_key = current["gemini_api_key"]

    if distill_engine is not None:
        de = distill_engine.strip().lower()
        final_distill = de if de in ("gemini_free", "main_api") else "gemini_free"
    else:
        final_distill = current["distill_engine"]

    if prov == "openrouter":
        final_base_url = "https://openrouter.ai/api/v1"
        ab_key = ""
        or_key = final_key
    elif prov == "abliteration":
        final_base_url = "https://api.abliteration.ai/v1"
        ab_key = final_key
        or_key = ""
    else:
        raw_url = (base_url or current["base_url"] or "https://api.abliteration.ai/v1").strip()
        final_base_url = raw_url.rstrip("/")
        ab_key = final_key
        or_key = ""

    port = current["port"]
    lines = [
        f"BASE_URL={final_base_url}",
        f"ABLIT_KEY={ab_key}",
        f"OPENROUTER_API_KEY={or_key}",
        f"ADMIN_KEY={final_admin}",
        f"DISTILL_ENGINE={final_distill}",
        f"GEMINI_API_KEY={final_gemini_key}",
        f"PORT={port}",
    ]

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_env = ENV_FILE.with_suffix(".env.tmp")
    tmp_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp_env, ENV_FILE)
    if os.name != "nt":
        try:
            os.chmod(ENV_FILE, 0o600)
        except OSError:
            pass

    os.environ["BASE_URL"] = final_base_url
    os.environ["ABLIT_KEY"] = ab_key
    os.environ["OPENROUTER_API_KEY"] = or_key
    os.environ["ADMIN_KEY"] = final_admin
    os.environ["DISTILL_ENGINE"] = final_distill
    os.environ["PORT"] = str(port)

    invalidate_balance_cache()
    return load_config()


def invalidate_balance_cache() -> None:
    _balance_cache["ts"] = 0.0
    _balance_cache["val"] = None
    _balance_cache["cache_key"] = ""


def get_async_openai_client() -> AsyncOpenAI:
    cfg = load_config()
    if not cfg["has_key"]:
        raise ValueError("API-ключ не настроен. Откройте «Настройки» и укажите ключ.")

    headers = {}
    if cfg["provider"] == "openrouter":
        headers = {
            "HTTP-Referer": f"http://localhost:{cfg['port']}",
            "X-Title": "NanoAgent Context Distiller",
        }

    return AsyncOpenAI(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        default_headers=headers,
        timeout=180.0,
    )


async def fetch_balance_async(force: bool = False) -> Optional[str]:
    cfg = load_config()
    cache_key = f"{cfg['provider']}:{cfg['masked_key']}:{cfg['has_admin_key']}"
    now = time.time()

    if (
        not force
        and _balance_cache["cache_key"] == cache_key
        and (now - float(_balance_cache["ts"])) < BALANCE_CACHE_TTL
    ):
        return _balance_cache["val"]  # type: ignore[return-value]

    result: Optional[str] = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            if cfg["provider"] == "openrouter" and cfg["has_key"]:
                resp = await http.get(
                    "https://openrouter.ai/api/v1/credits",
                    headers={"Authorization": f"Bearer {cfg['api_key']}"},
                )
                if resp.status_code == 200:
                    d = resp.json().get("data", {})
                    tot = float(d.get("total_credits", 0))
                    usage = float(d.get("total_usage", 0))
                    remaining = max(0.0, tot - usage)
                    result = f"${remaining:.4f}"
            elif cfg["has_admin_key"] and cfg["provider"] in ("abliteration", "custom"):
                resp = await http.get(
                    "https://api.abliteration.ai/v1/organization/balance",
                    headers={"Authorization": f"Bearer {cfg['admin_key']}"},
                )
                if resp.status_code == 200:
                    avail = float(resp.json().get("available_usd", 0))
                    result = f"${avail:.4f}"
    except Exception as e:
        print(f"[NanoAgent] Ошибка получения баланса: {e}")
        return _balance_cache["val"] if _balance_cache["cache_key"] == cache_key else None  # type: ignore[return-value]

    _balance_cache["ts"] = now
    _balance_cache["val"] = result
    _balance_cache["cache_key"] = cache_key
    return result


def get_models_catalog(provider: str) -> List[dict]:
    if provider == "openrouter":
        return [
            {
                "id": "deepseek/deepseek-v4.1-flash",
                "name": "DeepSeek V4.1 Flash",
                "short_name": "Flash 1M",
                "icon": "zap",
                "badge": "Быстрая",
                "context": "1M контекст",
                "max_context": 1000000,
                "desc": "Ультрабыстрый отклик, идеальна для кода, файлов и терминала",
                "supports_reasoning": False,
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "short_name": "Claude 3.5",
                "icon": "sparkles",
                "badge": "Топ для кода",
                "context": "200k контекст",
                "max_context": 200000,
                "desc": "Высочайшая точность при работе с проектами и рефакторингом",
                "supports_reasoning": False,
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "short_name": "GPT-4o",
                "icon": "cpu",
                "badge": "Универсал",
                "context": "128k контекст",
                "max_context": 128000,
                "desc": "Надёжная флагманская модель OpenAI с точным вызовом инструментов",
                "supports_reasoning": False,
            },
            {
                "id": "qwen/qwen-2.5-72b-instruct",
                "name": "Qwen 2.5 72B Instruct",
                "short_name": "Qwen 2.5",
                "icon": "code",
                "badge": "Код",
                "context": "128k контекст",
                "max_context": 128000,
                "desc": "Мощная открытая модель для программирования и анализа",
                "supports_reasoning": False,
            },
            {
                "id": "deepseek/deepseek-chat",
                "name": "DeepSeek V3 (Chat)",
                "short_name": "DeepSeek V3",
                "icon": "layers",
                "badge": "Баланс",
                "context": "64k контекст",
                "max_context": 64000,
                "desc": "Экономичный универсальный стандарт для ежедневных задач",
                "supports_reasoning": False,
            },
            {
                "id": "deepseek/deepseek-r1",
                "name": "DeepSeek R1 (Reasoning)",
                "short_name": "DeepSeek R1",
                "icon": "brain",
                "badge": "CoT",
                "context": "164k контекст",
                "max_context": 164000,
                "desc": "Глубокие пошаговые рассуждения перед ответом",
                "supports_reasoning": True,
            },
        ]

    # abliteration / custom
    return [
        {
            "id": "abliterated-model-large-flash",
            "name": "Flash 1M (DeepSeek V4.1 Flash)",
            "short_name": "Flash 1M",
            "icon": "zap",
            "badge": "Быстрая",
            "context": "1M контекст",
            "max_context": 1000000,
            "desc": "Ультрабыстрая разблокированная модель, 1M токенов, идеальна для кода и команд",
            "supports_reasoning": True,
        },
        {
            "id": "abliterated-model",
            "name": "Qwen 3.5 (Abliterated)",
            "short_name": "Qwen 3.5",
            "icon": "cpu",
            "badge": "Баланс",
            "context": "256k контекст",
            "max_context": 256000,
            "desc": "Сбалансированная модель на базе Qwen 3.5, глубокая логика и точность",
            "supports_reasoning": True,
        },
        {
            "id": "abliterated-model-large-v2",
            "name": "GLM-5.3 Large v2",
            "short_name": "GLM-5.3 Large",
            "icon": "layers",
            "badge": "Large",
            "context": "1M контекст",
            "max_context": 1000000,
            "desc": "Тяжелая флагманская модель с огромным контекстом для сложного анализа",
            "supports_reasoning": True,
        },
        {
            "id": "abliterated-model-large",
            "name": "Abliterated Large v1",
            "short_name": "Large v1",
            "icon": "sparkles",
            "badge": "Классика",
            "context": "1M контекст",
            "max_context": 1000000,
            "desc": "Предыдущая ревизия 1M Large модели",
            "supports_reasoning": True,
        },
    ]


def get_default_distill_model(provider: str) -> str:
    if provider == "openrouter":
        return "deepseek/deepseek-v4.1-flash"
    return "abliterated-model-large-flash"


def load_base_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE.exists():
        try:
            txt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
            if txt:
                return txt
        except Exception:
            pass
    return DEFAULT_BASE_SYSTEM_PROMPT


def save_base_system_prompt(content: str) -> str:
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("Системный промпт не может быть пустым")
    tmp = SYSTEM_PROMPT_FILE.with_suffix(".txt.tmp")
    tmp.write_text(cleaned + "\n", encoding="utf-8")
    os.replace(tmp, SYSTEM_PROMPT_FILE)
    return cleaned


def reset_base_system_prompt() -> str:
    return save_base_system_prompt(DEFAULT_BASE_SYSTEM_PROMPT)


def build_full_system_prompt(
    cwd: str,
    mode: str,
    execution_allowed: bool,
    active_memory: Optional[str] = None,
) -> str:
    base = load_base_system_prompt()
    sys_name = platform.system()
    shell_name = "PowerShell" if os.name == "nt" else "Bash (/bin/bash)"

    env_block = (
        "\n\n=== ОКРУЖЕНИЕ И ИНСТРУМЕНТЫ ===\n"
        f"- ОС: {sys_name} | Терминал: {shell_name}\n"
        f"- Текущая рабочая директория (cwd): {cwd}\n"
        "- Доступные инструменты:\n"
        "  * read_file — чтение файлов с номерами строк\n"
        "  * list_dir — обзор структуры каталогов\n"
        "  * search_files — поиск по тексту/регулярным выражениям в файлах\n"
        "  * write_file — создание или полная перезапись файла\n"
        "  * edit_file — точечная замена фрагмента файла (возвращает diff)\n"
        "  * bash — выполнение команд в терминале (cd сохраняется между вызовами)"
    )

    if mode == "plan" and not execution_allowed:
        mode_block = (
            "\n\n=== АКТИВНЫЙ РЕЖИМ: ПЛАНИРОВАНИЕ (READ-ONLY) ===\n"
            "Сейчас активен режим обсуждения и планирования. Инструменты изменения системы "
            "(bash, write_file, edit_file) временно ОТКЛЮЧЕНЫ на уровне ядра.\n"
            "- Ты МОЖЕШЬ свободно использовать read_file, list_dir и search_files, чтобы изучить проект и дать точный ответ.\n"
            "- Сформируй подробный, конкретный и пошаговый план действий.\n"
            "- В конце ответа спроси пользователя: «Приступаем к выполнению плана? (нажмите «Выполнить план» или напишите «делай»)»."
        )
    else:
        mode_block = (
            "\n\n=== АКТИВНЫЙ РЕЖИМ: ВЫПОЛНЕНИЕ (ACT) ===\n"
            "Тебе открыт полный доступ ко всем 6 инструментам.\n"
            "- Действуй последовательно: изучай -> меняй -> проверяй результат запуском тестов или команд.\n"
            "- Не читай огромные файлы целиком без необходимости — используй start_line/end_line или search_files."
        )

    mem_block = ""
    if active_memory and active_memory.strip():
        mem_block = (
            "\n\n=======================================================\n"
            "АКТУАЛЬНАЯ РАБОЧАЯ ПАМЯТЬ АГЕНТА (ACTIVE MEMORY):\n"
            f"{active_memory.strip()}\n"
            "=======================================================\n"
            "ВАЖНОЕ ПРАВИЛО: Опирайся на факты, пути, IP-адреса, токены и решения из Active Memory. "
            "Не повторяй подходы из раздела «Что проверено и НЕ сработало»."
        )

    return base + env_block + mode_block + mem_block

# 🧠 NanoAgent v2.0 (Context Distiller Edition)

**NanoAgent v2.0** — лёгкий, асинхронный AI-агент для **Windows**, **Linux** и **macOS** в стиле Claude Code с 6 встроенными инструментами, архитектурным разделением режимов **План / Авто**, мгновенной остановкой задач и потокобезопасным фоновым сжатием контекста (**Active Memory Consolidation**).

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://kernel.org)
[![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=apple&logoColor=white)](https://apple.com)

---

## ✨ Возможности NanoAgent v2.0

* 🛠️ **6 встроенных кроссплатформенных инструментов:**
  * `read_file` — чтение файлов с нумерацией строк и диапазонами;
  * `list_dir` — обзор дерева каталогов с пропуском `.git`, `node_modules`, `venv`, `__pycache__`;
  * `search_files` — быстрый поиск по регулярным выражениям (`ripgrep` или встроенный Python-движок);
  * `write_file` — создание и перезапись файлов без проблем shell-экранирования;
  * `edit_file` — точечные правки с отображением наглядного `unified diff` прямо в чате;
  * `bash` — терминал (Bash на Linux/macOS, PowerShell на Windows) с сохранением `cd` между вызовами и защитой контекста от слишком длинных логов.
* 🧭 **Режимы «План» и «Авто» на уровне ядра:**
  * В режиме **🧭 План** мутирующие инструменты (`bash`, `write_file`, `edit_file`) физически отключены — агент изучает проект, составляет подробный план и ждёт нажатия **«▶️ Выполнить план»** (или подтверждения в чате).
  * В режиме **⚡ Авто** агент работает полностью автономно.
* ⏹ **Кнопка «Стоп» (`POST /api/chat/stop`):** мгновенно прерывает поток ответа модели и завершает дерево запущенных подпроцессов.
* 🧠 **Потокобезопасный Context Distiller (Active Memory):**
  * Неблокирующая фоновая консолидация старых этапов работы в компактную **Рабочую память** без потери параллельно добавляемых сообщений.
  * Атомарное скользящее окно (`TurnUnit`), не ломающее пары `tool_calls` / `tool` даже при жёстком ограничении бюджета (`16k`–`128k` токенов).
* ⚡ **Удобный веб-интерфейс:** выбор модели в 1 клик, настройка API-ключей и редактирование `system_prompt.txt` прямо в браузере, поиск и переименование диалогов, смена рабочей папки сессии (`📁 cwd`), копирование блоков кода.
* 🌐 **Поддержка провайдеров:** **Abliteration AI**, **OpenRouter** и любой кастомный OpenAI-совместимый API.

---

## 🚀 Быстрая установка и запуск

### 🪟 Windows

#### Вариант 1. Установка в 1 строчку (PowerShell):
```powershell
irm https://raw.githubusercontent.com/IgorSirosh/nano-agent/main/install.ps1 | iex
```

#### Вариант 2. Запуск из архива:
1. [**Скачайте репозиторий (ZIP)**](https://github.com/IgorSirosh/nano-agent/archive/refs/heads/main.zip) и распакуйте.
2. Запустите **`start.bat`** — откроется браузер на **http://localhost:5051**.

---

### 🐧 Linux и 🍎 macOS

#### Вариант 1. Установка в 1 строчку:
```bash
curl -fsSL https://raw.githubusercontent.com/IgorSirosh/nano-agent/main/install.sh | bash
```

#### Вариант 2. Ручной запуск или Docker:
```bash
git clone https://github.com/IgorSirosh/nano-agent.git
cd nano-agent
./start.sh
# или через Docker:
# docker compose up -d
```

---

## ⚙️ Настройка API-ключей и системного промпта

1. Откройте **http://localhost:5051** (при первом запуске без ключа окно настроек откроется автоматически, также доступно по кнопке **⚙️ Настройки**).
2. На вкладке **🔑 API и провайдер** выберите провайдера и введите ключ (`ak_...` или `sk-or-v1-...`). Ключ хранится локально в `.env` (на POSIX права `600`).
3. На вкладке **📝 Системный промпт** можно в любой момент отредактировать или сбросить базовые инструкции агента (`system_prompt.txt`).

---

## 📄 Лицензия

MIT License © 2026 Igor Sirosh

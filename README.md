# 🧠 NanoAgent (Context Distiller Edition)

**NanoAgent** — ультралёгкий автономный AI-ассистент для **Windows**, **Linux** и **macOS** в стиле Claude Code с прямым доступом к терминалу (PowerShell / Bash), интеллектуальным фоновым сжатием контекста (**Active Memory Consolidation**) и удобным веб-интерфейсом.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://kernel.org)
[![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=apple&logoColor=white)](https://apple.com)

---

## ✨ Ключевые возможности

* 💻 **Полноценный доступ к терминалу:**  
  * **Windows:** Нативная работа через **PowerShell** (управление файлами, процессы, запуск скриптов, сетевые утилиты).  
  * **Linux / macOS:** Прямой доступ к **Bash**.  
  Агент сам исследует окружение, пишет код, исправляет ошибки и показывает вывод команд с таймерами в реальном времени.
* 🧠 **Умное сжатие контекста (Context Distiller):**  
  Фоновый процесс анализирует длинную историю диалога и консольных выводов, дистиллируя их в лаконичную **«Рабочую память» (Active Memory)**. Это позволяет вести бесконечные многодневные сессии без переполнения лимита токенов.
* ⚡ **Мгновенный выбор моделей в 1 клик:**
  * `⚡ Flash 1M (DeepSeek V4.1 Flash)` — 1M контекст, ультрабыстрый отклик (480 т/с), идеален для работы в консоли.
  * `🧠 Qwen 3.5 (Abliterated)` — 256k контекст, сбалансированная логика без цензуры.
  * `🏋️ GLM-5.3 Large v2` — 1M контекст, тяжелая флагманская модель для сложного анализа.
  * `⚙️ Кастомные модели` — ввод любого собственного ID модели.
* 🌐 **Мультипровайдерность:** Поддержка **Abliteration AI** (без цензуры), **OpenRouter API** (Claude 3.5 Sonnet, GPT-4o, DeepSeek R1) и любого кастомного OpenAI-совместимого сервера.
* ⚙️ **Настройки прямо в браузере (Zero-Terminal Setup):** При первом запуске веб-интерфейс сам предложит ввести API-ключ и проверит баланс. Никаких правок конфигов вручную!
* 🚀 **Без тяжелых зависимостей:** Чистый Vanilla HTML/CSS/JS фронтенд и микро-бэкенд на FastAPI. Запуск за 2 секунды.

---

## 🚀 Быстрая установка и запуск

### 🪟 Для пользователей Windows

#### Вариант 1. Установка в 1 строчку (PowerShell):
Откройте **PowerShell** и вставьте команду:
```powershell
irm https://raw.githubusercontent.com/IgorSirosh/nano-agent/main/install.ps1 | iex
```
Скрипт сам создаст окружение, подтянет нужные пакеты, запустит сервер и откроет браузер.

#### Вариант 2. Запуск в 1 клик (без командной строки):
1. [**Скачайте репозиторий в архиве (ZIP)**](https://github.com/IgorSirosh/nano-agent/archive/refs/heads/main.zip) и распакуйте в любую папку.
2. Дважды кликните по файлу **`start.bat`**.
3. Откроется браузер на странице **http://localhost:5051**.

---

### 🐧 Для пользователей Linux и 🍎 macOS

#### Вариант 1. Установка в 1 строчку (Терминал):
```bash
curl -fsSL https://raw.githubusercontent.com/IgorSirosh/nano-agent/main/install.sh | bash
```

#### Вариант 2. Ручной запуск:
```bash
git clone https://github.com/IgorSirosh/nano-agent.git
cd nano-agent
./start.sh
```

#### Вариант 3. Запуск через Docker:
```bash
git clone https://github.com/IgorSirosh/nano-agent.git
cd nano-agent
docker compose up -d
```
Откройте в браузере: **http://localhost:5051**

---

## ⚙️ Настройка API-ключей

При первом открытии страницы в браузере появится окно настроек:

1. Выберите провайдера:
   * **Abliteration AI** — вставьте ваш ключ (`ak_...`). Опционально можно указать `Admin Key` для отображения баланса.
   * **OpenRouter** — вставьте ваш ключ (`sk-or-v1-...`).
   * **Свой сервер** — укажите Base URL и токен.
2. Нажмите **«Сохранить»** — агент готов к работе!

Ключи сохраняются локально в `.env` на вашей машине и никогда никуда не передаются.

---

## 🔒 Безопасность

* Агент по умолчанию работает в режиме **рассуждений и планирования**: сначала предлагает план и шаги решения, а команды в терминале запускает только после вашего подтверждения.
* Файлы сессий хранятся исключительно локально на вашей машине в папке `data/sessions/`.

---

## 📄 Лицензия

MIT License © 2026 Igor Sirosh

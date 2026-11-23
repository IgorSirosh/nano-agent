# 🧠 NanoAgent (Context Distiller Edition)

**NanoAgent** — ультралёгкий автономный AI-ассистент для Linux/macOS/Windows в стиле Claude Code с прямым доступом к локальному bash-терминалу, интеллектуальным фоновым сжатием контекста (**Active Memory Consolidation**) и удобным веб-интерфейсом.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## ✨ Ключевые возможности

* 💻 **Прямой доступ к Bash-терминалу:** Агент самостоятельно исследует файлы, проверяет сетевые соединения, пишет скрипты и запускает команды на вашей машине в реальном времени.
* 🧠 **Умное сжатие контекста (Context Distiller):** Фоновый процесс анализирует длинную историю команд и промежуточные ошибки, дистиллируя их в лаконичную **«Рабочую память» (Active Memory)**. Это позволяет вести бесконечные многодневные сессии без переполнения лимита токенов.
* ⚡ **Мгновенный выбор моделей в 1 клик:**
  * `⚡ Flash 1M (DeepSeek V4.1 Flash)` — 1M контекст, ультрабыстрый отклик (480 т/с), идеален для консоли.
  * `🧠 Qwen 3.5 (Abliterated)` — 256k контекст, сбалансированная логика без цензуры.
  * `🏋️ GLM-5.3 Large v2` — 1M контекст, тяжелая флагманская модель для сложного анализа.
  * `⚙️ Кастомные модели` — ввод любого собственного ID модели.
* 🌐 **Мультипровайдерность:** Поддержка **Abliteration AI** (без цензуры), **OpenRouter API** (Claude 3.5 Sonnet, GPT-4o, DeepSeek R1) и любого кастомного OpenAI-совместимого сервера.
* ⚙️ **Настройки прямо в браузере (Zero-Terminal Setup):** При первом запуске веб-интерфейс сам предложит ввести API-ключ и проверит баланс. Никаких правок конфигов вручную!
* 🚀 **Без тяжелых сборщиков:** Чистый Vanilla HTML/CSS/JS фронтенд и микро-бэкенд на FastAPI. Запуск за 2 секунды.

---

## 🚀 Быстрый старт

### Вариант 1. Запуск одной строчкой (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/IgorSirosh/nano-agent/main/install.sh | bash
```

### Вариант 2. Запуск через Docker

```bash
git clone https://github.com/IgorSirosh/nano-agent.git
cd nano-agent
docker compose up -d
```
Откройте в браузере: **http://localhost:5051**

### Вариант 3. Ручной запуск (Linux / macOS)

```bash
git clone https://github.com/IgorSirosh/nano-agent.git
cd nano-agent
./start.sh
```

### Вариант 4. Запуск на Windows

1. Скачайте репозиторий (ZIP) и распакуйте.
2. Дважды кликните по файлу **`start.bat`**.
3. Браузер откроет страницу **http://localhost:5051**.

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
* Файлы сессий хранятся локально в папке `data/sessions/`.

---

## 📄 Лицензия

MIT License © 2026 Igor Sirosh

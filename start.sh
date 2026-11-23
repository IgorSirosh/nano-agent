#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🧠 Запуск NanoAgent..."

# Создаем venv если нет
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения Python..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip -q
    echo "⬇️ Установка зависимостей..."
    ./venv/bin/pip install -r requirements.txt -q
fi

# Проверка .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        touch .env
    fi
fi

mkdir -p data/sessions

echo "🚀 NanoAgent запущен! Откройте в браузере:"
echo "👉 http://localhost:5051"

./venv/bin/python3 server.py

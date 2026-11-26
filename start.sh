#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🧠 Запуск NanoAgent v2.0..."

if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения Python..."
    python3 -m venv venv
fi

REQ_HASH=$(sha256sum requirements.txt | awk '{print $1}')
STAMP_FILE="venv/.installed_reqs"
INSTALLED_HASH=""
if [ -f "$STAMP_FILE" ]; then
    INSTALLED_HASH=$(cat "$STAMP_FILE")
fi

if [ "$REQ_HASH" != "$INSTALLED_HASH" ]; then
    echo "⬇️ Установка/обновление зависимостей из requirements.txt..."
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q
    echo "$REQ_HASH" > "$STAMP_FILE"
fi

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

exec ./venv/bin/python3 server.py

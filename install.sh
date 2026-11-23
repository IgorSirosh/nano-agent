#!/usr/bin/env bash
set -e

INSTALL_DIR="${HOME}/.nano-agent"
REPO_URL="https://github.com/IgorSirosh/nano-agent.git"

echo "🧠 Установка автономного агента NanoAgent..."

if [ -d "$INSTALL_DIR" ]; then
    echo "📦 Найдена существующая установка, обновляем..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "⬇️ Клонирование репозитория в $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

./start.sh

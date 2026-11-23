@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 🧠 Запуск NanoAgent для Windows...

if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

if not exist ".env" (
    if exist ".env.example" copy .env.example .env
)

if not exist "data\sessions" (
    mkdir data\sessions
)

echo.
echo 🚀 NanoAgent запущен!
echo 👉 Откройте браузер: http://localhost:5051
echo.
python server.py
pause

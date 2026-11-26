@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 🧠 Запуск NanoAgent v2.0 для Windows...

if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

call venv\Scripts\activate.bat

for /f "usebackq tokens=*" %%h in (`powershell -NoProfile -Command "(Get-FileHash 'requirements.txt' -Algorithm SHA256).Hash"`) do set REQ_HASH=%%h
set INSTALLED_HASH=
if exist "venv\.installed_reqs" (
    set /p INSTALLED_HASH=<"venv\.installed_reqs"
)

if not "%REQ_HASH%"=="%INSTALLED_HASH%" (
    echo ⬇️ Установка и обновление зависимостей...
    python -m pip install --upgrade pip -q
    pip install -r requirements.txt -q
    > "venv\.installed_reqs" echo %REQ_HASH%
)

if not exist ".env" (
    if exist ".env.example" copy .env.example .env >nul
)

if not exist "data\sessions" (
    mkdir data\sessions
)

echo.
echo 🚀 NanoAgent v2.0 запущен!
echo 👉 Откройте браузер: http://localhost:5051
echo.
python server.py
pause

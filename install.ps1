# PowerShell 1-Click Installer for NanoAgent
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   🧠 Установка NanoAgent для Windows     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Проверка Python
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonCmd) {
    $pythonCmd = (Get-Command py -ErrorAction SilentlyContinue).Source
}

if (-not $pythonCmd) {
    Write-Host "❌ Python не найден в системе!" -ForegroundColor Red
    Write-Host "Пожалуйста, установите Python 3.10+ с https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "(ОБЯЗАТЕЛЬНО отметьте галочку: 'Add Python to PATH' при установке)" -ForegroundColor Yellow
    Pause
    exit 1
}

# 2. Директория установки
$installDir = Join-Path $HOME ".nano-agent"
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}
Set-Location $installDir

# 3. Скачивание кода
if (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path (Join-Path $installDir ".git")) {
        Write-Host "📦 Обновление существующей версии..." -ForegroundColor Green
        git pull
    } else {
        Write-Host "⬇️ Клонирование репозитория с GitHub..." -ForegroundColor Green
        git clone https://github.com/IgorSirosh/nano-agent.git .
    }
} else {
    Write-Host "⬇️ Загрузка архива с GitHub..." -ForegroundColor Green
    $zipUrl = "https://github.com/IgorSirosh/nano-agent/archive/refs/heads/main.zip"
    $zipFile = Join-Path $installDir "nano-agent.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile
    Expand-Archive -Path $zipFile -DestinationPath $installDir -Force
    Remove-Item $zipFile -Force
    $extracted = Join-Path $installDir "nano-agent-main"
    if (Test-Path $extracted) {
        Get-ChildItem -Path $extracted | Move-Item -Destination $installDir -Force
        Remove-Item $extracted -Recurse -Force
    }
}

Write-Host "🚀 Запуск NanoAgent..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -ArgumentList "/c start.bat"
Start-Sleep -Seconds 2
Start-Process "http://localhost:5051"

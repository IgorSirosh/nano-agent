# PowerShell 1-Click Installer for NanoAgent v2.0
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   🧠 Установка NanoAgent v2.0 (Windows)  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonCmd) {
    $pythonCmd = (Get-Command py -ErrorAction SilentlyContinue).Source
}

if (-not $pythonCmd) {
    Write-Host "❌ Python не найден в системе!" -ForegroundColor Red
    Write-Host "Установите Python 3.10+ с https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "(ОБЯЗАТЕЛЬНО отметьте галочку 'Add Python to PATH')" -ForegroundColor Yellow
    Pause
    exit 1
}

$installDir = Join-Path $HOME ".nano-agent"
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}
Set-Location $installDir

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
        Get-ChildItem -Path $extracted -Force | Move-Item -Destination $installDir -Force
        Remove-Item $extracted -Recurse -Force
    }
}

Write-Host "🚀 Запуск сервера NanoAgent..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -ArgumentList "/c start.bat"

Write-Host "⏳ Ожидание готовности http://localhost:5051/api/status (до 45 сек)..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:5051/api/status" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ready) {
    Write-Host "✅ NanoAgent готов к работе! Открываем браузер..." -ForegroundColor Green
} else {
    Write-Host "⚠️ Сервер запускается дольше обычного, открываем браузер..." -ForegroundColor Yellow
}
Start-Process "http://localhost:5051"

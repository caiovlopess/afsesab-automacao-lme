<#
.SYNOPSIS
  Sobe o AF Copilot: ai-backend + desktop-client.
.EXAMPLE
  .\start.ps1
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[1/3] Iniciando ai-backend..." -ForegroundColor Cyan
$backend = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
  '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
  "cd '$root\ai-backend'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
) -PassThru -WindowStyle Normal

Write-Host "[2/3] Aguardando /health..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 1
  try {
    $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8000/health'
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch { }
}
if (-not $ready) {
  Write-Host "Backend nao respondeu. Verifique pip-install.log e os logs." -ForegroundColor Red
  exit 1
}
Write-Host "Backend OK: $((Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/health').Content)" -ForegroundColor Green

Write-Host "[3/3] Iniciando Electron..." -ForegroundColor Cyan
Set-Location "$root\desktop-client"
npm start

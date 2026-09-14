# Run Recovery & Automation (works when .venv\Scripts\activate.ps1 is blocked)
Set-Location $PSScriptRoot
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    & $python -m pip install -r requirements.txt
}

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example — set DEFENDRA_API_EMAIL / PASSWORD"
}

Write-Host "Starting Recovery & Automation on http://127.0.0.1:8001"
& $python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

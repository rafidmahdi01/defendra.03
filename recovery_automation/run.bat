@echo off
REM Run Recovery & Automation without activating the venv (avoids PowerShell script policy).
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist ".env" (
    echo Copying .env.example to .env ...
    copy /Y .env.example .env
)

echo Starting Recovery ^& Automation on http://127.0.0.1:8001
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

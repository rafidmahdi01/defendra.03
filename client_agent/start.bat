@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
set "ROOT=!ROOT:~0,-1!"
cd /d "!ROOT!"

echo.
echo ============================================
echo   Defendra Client Agent (v2.0+)
echo ============================================
echo.
echo WARNING: This is the standalone agent runner.
echo          For full Defendra suite, see: install.bat
echo.
echo This will start the Client Agent which:
echo   - Scans for threats (USB, email, processes)
echo   - Creates local + cloud backups
echo   - Monitors system behavior
echo   - Sends events to dashboard
echo.
echo Make sure backend is running at http://127.0.0.1:8000
echo (if using full suite, also start recovery_automation at port 8001)
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    echo        Install Python 3.11+ and add it to PATH.
    pause
    exit /b 1
)

if not exist "!ROOT!\.env" (
    if exist "!ROOT!\.env.example" (
        copy /Y "!ROOT!\.env.example" "!ROOT!\.env"
        echo Configuration file created: .env
    )
)

echo.
echo Waiting for backend at http://127.0.0.1:8000 ...
:wait_backend
curl -s --max-time 3 http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 (
    echo Waiting... (Ctrl+C to cancel)
    timeout /t 2 /nobreak >nul
    goto wait_backend
)

echo Backend detected. Starting Client Agent (Ctrl+C to stop)...
echo.
python -u "!ROOT!\main.py"

pause

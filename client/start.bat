@echo off
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

echo ============================================
echo   Defendra Client Server
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and try again.
    pause
    exit /b 1
)

if not exist "%ROOT%\.env" (
    echo Creating .env from .env.example ...
    copy /Y "%ROOT%\.env.example" "%ROOT%\.env"
    echo.
    echo NOTE: Uses admin@defendra.com / Admin@1234 when backend is bootstrapped.
    echo.
)

if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv "%ROOT%\.venv"
    "%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt"
) else (
    "%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt" -q
)

echo Waiting for Defendra backend at http://127.0.0.1:8000 ...
:wait_backend
curl -s --max-time 3 http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_backend
)
echo Backend is ready.

echo Bootstrapping admin account if needed...
curl -s -X POST http://127.0.0.1:8000/api/auth/bootstrap-admin ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@defendra.com\",\"full_name\":\"Defendra Admin\",\"password\":\"Admin@1234\",\"role\":\"admin\"}" >nul 2>&1

echo.
echo Starting client server (Ctrl+C to stop)...
echo Dashboard: http://localhost:5173
echo.

"%ROOT%\.venv\Scripts\python.exe" -u "%ROOT%\main.py"

echo.
echo Client server stopped.
pause

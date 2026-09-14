@echo off
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

echo ============================================
echo   Defendra.AI - Starting all services
echo ============================================

:: Pre-flight checks
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12+ and try again.
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install Node.js LTS and try again.
    pause
    exit /b 1
)

:: Auto-setup: env files
if not exist "%ROOT%\backend\.env" (
    echo Creating backend\.env from .env.example ...
    copy /Y "%ROOT%\backend\.env.example" "%ROOT%\backend\.env"
)
if not exist "%ROOT%\client\.env" (
    echo Creating client\.env from .env.example ...
    copy /Y "%ROOT%\client\.env.example" "%ROOT%\client\.env"
)
if not exist "%ROOT%\recovery_automation\.env" (
    echo Creating recovery_automation\.env from .env.example ...
    copy /Y "%ROOT%\recovery_automation\.env.example" "%ROOT%\recovery_automation\.env"
)

:: Auto-setup: Python venv (backend)
if not exist "%ROOT%\backend\.venv\Scripts\python.exe" (
    echo Creating backend virtual environment...
    python -m venv "%ROOT%\backend\.venv"
    "%ROOT%\backend\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\backend\requirements.txt"
)

:: Auto-setup: Python venv (client server)
if not exist "%ROOT%\client\.venv\Scripts\python.exe" (
    echo Creating client virtual environment...
    python -m venv "%ROOT%\client\.venv"
    "%ROOT%\client\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\client\requirements.txt"
)

:: Auto-setup: Python venv (recovery_automation)
if not exist "%ROOT%\recovery_automation\.venv\Scripts\python.exe" (
    echo Creating recovery_automation virtual environment...
    python -m venv "%ROOT%\recovery_automation\.venv"
    "%ROOT%\recovery_automation\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\recovery_automation\requirements.txt"
)

:: Auto-setup: Root Node dependencies (electron, cross-env, etc.)
if not exist "%ROOT%\node_modules" (
    echo Installing root dependencies (Electron, cross-env^)...
    npm --prefix "%ROOT%" install
)

:: Auto-setup: Frontend Node dependencies
if not exist "%ROOT%\frontend\node_modules" (
    echo Installing frontend dependencies...
    npm --prefix "%ROOT%\frontend" install
)

:: Kill leftover processes from previous runs
echo Cleaning up any leftover processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
timeout /t 3 /nobreak >nul

echo [1/5] Starting Backend API on http://127.0.0.1:8000 ...
start "Backend" cmd /k "cd /d "%ROOT%\backend" && .venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo     Waiting for backend to be ready...
:wait_backend
timeout /t 2 /nobreak >nul
curl -s --max-time 3 http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 goto wait_backend
echo     Backend is ready.

echo Bootstrapping admin user (admin@defendra.com) if needed...
curl -s -X POST http://127.0.0.1:8000/api/auth/bootstrap-admin ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@defendra.com\",\"full_name\":\"Defendra Admin\",\"password\":\"Admin@1234\",\"role\":\"admin\"}" >nul 2>&1

echo [2/5] Starting Recovery ^& Automation on http://127.0.0.1:8001 ...
start "Recovery" cmd /k "cd /d "%ROOT%\recovery_automation" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"
timeout /t 3 /nobreak >nul

echo [3/5] Starting Frontend on http://localhost:5173 ...
start "Frontend" cmd /k "cd /d "%ROOT%" && npm run frontend:dev"
timeout /t 5 /nobreak >nul

echo [4/5] Starting Electron...
start "Electron" cmd /k "cd /d "%ROOT%" && npm run electron:dev"
timeout /t 3 /nobreak >nul

echo [5/5] Starting Client Server (endpoint agent)...
start "Client Server" cmd /k "cd /d "%ROOT%\client" && .venv\Scripts\python.exe -u main.py"

echo.
echo ============================================
echo   All services started successfully!
echo   Dashboard:    http://localhost:5173
echo   API:          http://127.0.0.1:8000
echo   API docs:     http://127.0.0.1:8000/docs
echo   Recovery:     http://127.0.0.1:8001
echo   Electron:     Desktop app opening...
echo.
echo   Endpoint agent: look for the separate terminal titled
echo                   "Client Server" (logs also in client\logs\agent.log)
echo.
echo   NOTE: client_agent\ is the OLD agent and is NOT started by
echo         start.bat. Only client\ (Client Server) runs now.
echo         Do not run both at the same time.
echo.
echo   Login:
echo     Email:    admin@defendra.com
echo     Password: Admin@1234
echo ============================================
echo.
pause

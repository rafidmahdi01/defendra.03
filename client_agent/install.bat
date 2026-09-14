@echo off
setlocal enabledelayedexpansion

set "AGENT_DIR=%~dp0"
set "AGENT_DIR=!AGENT_DIR:~0,-1!"
set "STARTUP_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "STARTUP_NAME=DefendraAgent"
set "ROOT_DIR=%AGENT_DIR%\.."

echo.
echo ============================================
echo   Defendra Security Suite - Full Installer
echo ============================================
echo.
echo   This will install:
echo   - Client Agent (threat scanning)
echo   - Backup Manager (local + cloud backup)
echo   - Browser Extension (security monitoring)
echo   - Recovery Service (backup centralization)
echo.

:: Check if running as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Some features require Administrator privileges.
    echo          (Extension registration, Windows startup)
)
echo.

:: Install Python dependencies
echo [1/5] Installing Python dependencies...
pip install --upgrade pip >nul 2>&1
pip install requests python-dotenv psutil watchdog pywin32 pyclamd huggingface_hub fastapi uvicorn boto3 >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies. Make sure Python 3.11+ and pip are installed.
    pause
    exit /b 1
)
echo       ✓ Dependencies installed.

:: Setup Client Backup Manager
echo [2/5] Setting up Backup Manager...
if not exist "%ROOT_DIR%\client\data\important" (
    mkdir "%ROOT_DIR%\client\data\important"
    echo.       Sample file for backup testing > "%ROOT_DIR%\client\data\important\sample.txt"
)
if not exist "%ROOT_DIR%\client\backups" (
    mkdir "%ROOT_DIR%\client\backups"
)
echo       ✓ Backup folders created.
echo       ✓ Backup Manager enabled (1 hour schedule).

:: Setup Recovery Automation Service
echo [3/5] Setting up Recovery Automation Service...
if not exist "%ROOT_DIR%\recovery_automation\.env" (
    if exist "%ROOT_DIR%\recovery_automation\.env.example" (
        copy /Y "%ROOT_DIR%\recovery_automation\.env.example" "%ROOT_DIR%\recovery_automation\.env"
        echo       ✓ Recovery service configuration created.
    )
)
if not exist "%ROOT_DIR%\recovery_automation\backups" (
    mkdir "%ROOT_DIR%\recovery_automation\backups"
)
echo       ✓ Recovery service ready (port 8001).

:: Setup Browser Extension
echo [4/5] Setting up Browser Extension...
if not exist "%ROOT_DIR%\extension\defendra-logo.png" (
    if exist "%ROOT_DIR%\frontend\src\assets\defendra-logo.png" (
        copy /Y "%ROOT_DIR%\frontend\src\assets\defendra-logo.png" "%ROOT_DIR%\extension\defendra-logo.png"
    )
)
echo       ✓ Extension files configured.
echo       Note: To enable in Chrome/Edge:
echo         1. Open chrome://extensions
echo         2. Enable "Developer mode"
echo         3. Click "Load unpacked"
echo         4. Select: %ROOT_DIR%\extension

:: Register in Windows startup (runs on login)
echo [5/5] Finalizing installation...
reg add "%STARTUP_KEY%" /v "%STARTUP_NAME%" /t REG_SZ /d "python \"%AGENT_DIR%\main.py\"" /f >nul 2>&1
if %errorlevel% neq 0 (
    echo       WARNING: Could not register startup. You may need Administrator privileges.
) else (
    echo       ✓ Agent registered for Windows startup.
)

echo.
echo ============================================
echo   ✓ Installation Complete!
echo ============================================
echo.
echo NEXT STEPS:
echo.
echo 1. START SERVICES:
echo    Terminal 1: cd backend ^&^& python main.py
echo    Terminal 2: cd recovery_automation ^&^& run.bat
echo    Terminal 3: cd client ^&^& python main.py
echo.
echo 2. INSTALL BROWSER EXTENSION:
echo    - Open chrome://extensions (or edge://extensions)
echo    - Enable "Developer mode" (top right)
echo    - Click "Load unpacked"
echo    - Select: %ROOT_DIR%\extension
echo.
echo 3. VERIFY BACKUP SYSTEM:
echo    - Files in: %ROOT_DIR%\client\data\important\
echo    - Local backups: %ROOT_DIR%\client\backups\
echo    - Server cache: %ROOT_DIR%\recovery_automation\backups\
echo    - Check: curl http://127.0.0.1:8001/backup/stats
echo.
echo 4. CONFIGURE SETTINGS:
echo    Edit these files as needed:
echo    - client\.env (backup interval, server URL)
echo    - recovery_automation\.env (S3 credentials, retention)
echo    - client_agent\.env (email scanning, API keys)
echo.
echo FEATURES ENABLED:
echo.
echo   ✓ Threat scanning (USB, email, processes)
echo   ✓ Local + Cloud backup (every hour)
echo   ✓ Browser security monitoring
echo   ✓ Centralized backup management
echo   ✓ Disaster recovery (one-click restore)
echo   ✓ Dashboard integration
echo.
echo To uninstall, run: uninstall.bat
echo.
pause
echo.
pause

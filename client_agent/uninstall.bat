@echo off
setlocal enabledelayedexpansion

set "STARTUP_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "STARTUP_NAME=DefendraAgent"
set "AGENT_DIR=%~dp0"
set "ROOT_DIR=!AGENT_DIR:~0,-1!\.."

echo.
echo ============================================
echo   Defendra Security Suite - Uninstaller
echo ============================================
echo.
echo This will uninstall:
echo   - Client Agent
echo   - Agent Windows startup hook
echo   - (Data and backups are preserved)
echo.

:: Remove from Windows startup
echo [1/3] Removing from Windows startup...
reg delete "%STARTUP_KEY%" /v "%STARTUP_NAME%" /f >nul 2>&1
if %errorlevel% eq 0 (
    echo       ✓ Removed from Windows startup.
) else (
    echo       INFO: Was not registered in startup.
)

:: Stop any running agent processes
echo [2/3] Stopping running agent processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Defendra*" >nul 2>&1
taskkill /F /IM "client_agent" >nul 2>&1

:: Clean up
echo [3/3] Cleanup...
if exist "!AGENT_DIR!\.env" (
    echo       Backing up .env to .env.backup
    copy /Y "!AGENT_DIR!\.env" "!AGENT_DIR!\.env.backup" >nul 2>&1
    del "!AGENT_DIR!\.env"
)

echo.
echo ============================================
echo   ✓ Uninstall Complete!
echo ============================================
echo.
echo DATA PRESERVED:
echo   - Backups: !ROOT_DIR!\client\backups\
echo   - Logs: !ROOT_DIR!\client\logs\
echo   - Config backup: !AGENT_DIR!\.env.backup
echo.
echo MANUAL CLEANUP:
echo   If you want to completely remove:
echo   1. Delete: !AGENT_DIR! (this folder)
echo   2. Delete: !ROOT_DIR!\client\
echo   3. Delete: !ROOT_DIR!\recovery_automation\ (optional)
echo.
echo Browser Extension:
echo   To remove, go to chrome://extensions and click "Remove"
echo.
echo To reinstall later, run: install.bat
echo.
pause

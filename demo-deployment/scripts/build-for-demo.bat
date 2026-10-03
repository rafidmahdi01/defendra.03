@echo off
REM ============================================================
REM Defendra.AI - Build Script for Demo Deployment
REM ============================================================
REM This script builds both frontend and backend for deployment
REM Run from the project root directory
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Defendra.AI Demo Build Script
echo ========================================
echo.

REM Check for required environment variables
if "%VITE_API_URL%"=="" (
    echo [WARN] VITE_API_URL not set. Using default: http://127.0.0.1:8000
    set VITE_API_URL=http://127.0.0.1:8000
)

if "%VITE_WS_URL%"=="" (
    echo [WARN] VITE_WS_URL not set. Using default: ws://127.0.0.1:8000/ws/dashboard
    set VITE_WS_URL=ws://127.0.0.1:8000/ws/dashboard
)

echo Configuration:
echo   API URL: %VITE_API_URL%
echo   WS URL:  %VITE_WS_URL%
echo.

REM ------------------------------------------------------------
REM Build Frontend
REM ------------------------------------------------------------
echo [1/3] Building frontend...
cd frontend

if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)

echo Building frontend with Vite...
call npm run build

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Frontend build failed!
    exit /b 1
)

echo [OK] Frontend built successfully!
cd ..

REM ------------------------------------------------------------
REM Prepare Backend
REM ------------------------------------------------------------
echo.
echo [2/3] Preparing backend...

if not exist backend\.venv (
    echo Creating Python virtual environment...
    cd backend
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
    cd ..
) else (
    echo [OK] Virtual environment already exists
)

REM ------------------------------------------------------------
REM Create deployment package
REM ------------------------------------------------------------
echo.
echo [3/3] Creating deployment package...

set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%
set PACKAGE_DIR=dist\defendra-demo-%TIMESTAMP%

if not exist dist mkdir dist
mkdir "%PACKAGE_DIR%"

REM Copy necessary files
echo Copying files...
xcopy /E /I /Q backend "%PACKAGE_DIR%\backend" > nul
xcopy /E /I /Q frontend\dist "%PACKAGE_DIR%\frontend\dist" > nul
xcopy /E /I /Q database "%PACKAGE_DIR%\database" > nul
xcopy /E /I /Q electron "%PACKAGE_DIR%\electron" > nul
copy package.json "%PACKAGE_DIR%\" > nul
copy render.yaml "%PACKAGE_DIR%\" > nul
copy docker-compose.yml "%PACKAGE_DIR%\" > nul

REM Create .env template
echo # Defendra.AI Environment Configuration > "%PACKAGE_DIR%\backend\.env"
echo DATABASE_URL=mysql+pymysql://crps_user:change-me@localhost:3306/cyber_resilience_db >> "%PACKAGE_DIR%\backend\.env"
echo JWT_SECRET_KEY=replace-with-64-char-random-string >> "%PACKAGE_DIR%\backend\.env"
echo ALLOWED_ORIGINS=http://localhost:5173,http://localhost >> "%PACKAGE_DIR%\backend\.env"
echo FIREBASE_PROJECT_ID=defendraai >> "%PACKAGE_DIR%\backend\.env"

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Deployment package created at:
echo   %CD%\%PACKAGE_DIR%
echo.
echo Next steps:
echo   1. Push code to GitHub
echo   2. Go to https://dashboard.render.com/blueprints
echo   3. Create new blueprint instance from your repo
echo.
echo Or for manual deployment:
echo   1. Copy the package to your server
echo   2. Configure environment variables
echo   3. Run: docker compose up --build
echo.

endlocal

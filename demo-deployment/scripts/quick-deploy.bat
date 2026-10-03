@echo off
REM ============================================================
REM Defendra.AI - Quick Deploy to Render
REM ============================================================
REM This script opens your browser to deploy Defendra.AI
REM ============================================================

echo.
echo ========================================
echo   Defendra.AI Quick Deploy
echo ========================================
echo.
echo This will help you deploy Defendra.AI to Render.com
echo.
echo Prerequisites:
echo   1. GitHub account with this code pushed
echo   2. Render.com account (free)
echo.
echo Steps:
echo   1. Push code to GitHub
echo   2. Sign in to Render.com
echo   3. Create Blueprint from your repo
echo.

pause

echo.
echo Opening Render Blueprint page...
start https://dashboard.render.com/blueprints

echo.
echo Opening GitHub to create new repo...
start https://github.com/new

echo.
echo ========================================
echo   Next Steps
echo ========================================
echo.
echo 1. Create a new GitHub repository
echo 2. Push this code:
echo    git init
echo    git add .
echo    git commit -m "Initial commit"
echo    git remote add origin https://github.com/YOUR_USERNAME/defendra.git
echo    git push -u origin main
echo.
echo 3. In Render, click "New Blueprint Instance"
echo 4. Select your repository
echo 5. Click "Apply"
echo.
echo Your demo will be live in ~10 minutes!
echo.
pause

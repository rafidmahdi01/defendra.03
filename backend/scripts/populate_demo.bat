@echo off
echo ========================================
echo  Defendra Demo Data Population
echo ========================================
echo.
echo This will add sample devices and alerts to your database.
echo.
pause

cd /d "%~dp0.."
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
echo Using %PYTHON%
%PYTHON% scripts\populate_demo_data.py

echo.
pause

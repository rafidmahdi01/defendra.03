@echo off
echo ========================================
echo  Defendra Demo Data Cleanup
echo ========================================
echo.
echo WARNING: This will delete all sample demo data from your database.
echo Only items tagged with 'sample_data: True' will be removed.
echo.
pause

cd /d "%~dp0.."
python scripts\delete_demo_data.py

echo.
pause

@echo off
REM Turret Start Script

echo.
echo ============================================================
echo  🎯 TURRET SYSTEM - STARTING
echo ============================================================
echo.

cd /d "C:\Users\User\OneDrive - Cyprus University of Technology\Desktop\projects\personal\turret"

echo Activating virtual environment...
call .\.venv\Scripts\activate.bat

echo Starting turret...
echo.

python src/main.py

echo.
echo ============================================================
echo  Turret stopped
echo ============================================================
pause


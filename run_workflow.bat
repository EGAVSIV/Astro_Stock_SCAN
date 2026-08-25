@echo off
TITLE AstroScan Workflow Manager
COLOR 0A

echo ========================================================
echo        STARTING ASTROSCAN WORKFLOW SERVER
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    pause
    exit /b
)

:: Install required dependencies
echo Installing/Checking Dependencies...
pip install flask flask-cors pandas pyarrow requests pyswisseph >nul 2>&1

:: Launch Workflow Server and Open Dashboard
echo Starting Local Workflow Engine...
start "" http://localhost:5000
python server.py

pause

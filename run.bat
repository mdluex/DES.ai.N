@echo off
title Des-ai-n Launcher
color 0E

echo ============================================
echo        Des-ai-n  -  AI Graphic Designer
echo ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

:: Install / upgrade requirements
echo [*] Checking dependencies...
pip install -r "%~dp0requirements.txt" --quiet >nul 2>&1
if errorlevel 1 (
    echo [!] pip install failed. Trying with --user flag...
    pip install -r "%~dp0requirements.txt" --user --quiet >nul 2>&1
)
echo [OK] Dependencies ready.
echo.

:: Create folders if missing
if not exist "%~dp0templates" mkdir "%~dp0templates"
if not exist "%~dp0output" mkdir "%~dp0output"

:: Launch the app
echo [*] Starting Des-ai-n...
echo.
python "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Application crashed. Check the error above.
    pause
)

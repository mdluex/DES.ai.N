@echo off
setlocal enableextensions
title Des-ai-n Launcher
color 0E

echo ============================================
echo        Des-ai-n  -  AI Graphic Designer
echo ============================================
echo.

cd /d "%~dp0"

:: ---------- 1. Check that Python is installed ----------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.10+ from https://python.org
    echo         and tick "Add Python to PATH" during setup.
    pause
    exit /b 1
)

:: ---------- 2. Prepare paths ----------
set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "FIRST_RUN=0"

:: ---------- 3. Create the virtual environment if missing ----------
if not exist "%VENV_PY%" (
    echo [*] First-time setup detected.
    echo [*] Creating an isolated virtual environment in .venv ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        echo         Make sure the 'venv' module is available - it ships with
        echo         standard Python installs from python.org.
        pause
        exit /b 1
    )
    echo [OK]  Virtual environment created.
    set "FIRST_RUN=1"
)

:: ---------- 4. Upgrade pip + install requirements INSIDE the venv ----------
echo [*] Updating pip ...
"%VENV_PY%" -m pip install --upgrade pip --disable-pip-version-check --quiet
if "%FIRST_RUN%"=="1" (
    echo [*] Installing project dependencies into .venv ...
) else (
    echo [*] Verifying / updating project dependencies ...
)
"%VENV_PY%" -m pip install -r "%~dp0requirements.txt" --disable-pip-version-check --quiet
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies inside the virtual environment.
    echo         To see the full error, run manually:
    echo             "%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
    echo.
    pause
    exit /b 1
)
echo [OK]  Dependencies are ready.
echo.

:: ---------- 5. Make sure working folders exist ----------
if not exist "%~dp0templates" mkdir "%~dp0templates"
if not exist "%~dp0output"    mkdir "%~dp0output"

:: ---------- 6. Launch the app using the venv's Python ----------
echo [*] Starting Des-ai-n ...
echo.
"%VENV_PY%" "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error. Scroll up for details.
    pause
)

endlocal

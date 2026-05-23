@echo off
setlocal enableextensions
title Des-ai-n Updater
color 0B

echo ============================================
echo        Des-ai-n  -  Update from GitHub
echo ============================================
echo.

cd /d "%~dp0"

set "REPO_URL=https://github.com/mdluex/DES.ai.N.git"
set "BRANCH=main"

:: ---------- 1. Check that git is installed ----------
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not in PATH.
    echo         Install Git for Windows from https://git-scm.com/download/win
    echo         and re-run this script.
    pause
    exit /b 1
)

:: ---------- 2. Make sure this folder is linked to the repo ----------
if not exist "%~dp0.git" (
    echo [WARN] This folder is not a git repository, so update.bat cannot
    echo        pull new commits into it directly.
    echo.
    echo Easiest fix - re-clone the project next to this folder:
    echo.
    echo     git clone %REPO_URL%
    echo.
    echo Or convert this folder into a git checkout yourself:
    echo.
    echo     git init
    echo     git remote add origin %REPO_URL%
    echo     git fetch origin
    echo     git checkout -t origin/%BRANCH%
    echo.
    pause
    exit /b 1
)

:: ---------- 3. Fetch + pull latest ----------
echo [*] Fetching latest changes from %REPO_URL% ...
git fetch origin
if errorlevel 1 (
    echo [ERROR] git fetch failed. Check your internet connection.
    pause
    exit /b 1
)

:: Get current branch so we pull the right one
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CURRENT=%%b"
if "%CURRENT%"=="" set "CURRENT=%BRANCH%"

echo [*] Current branch: %CURRENT%
echo [*] Pulling latest commits (fast-forward only) ...
git pull --ff-only origin %CURRENT%
if errorlevel 1 (
    echo.
    echo [WARN] git pull failed. This usually means you have local commits
    echo        or uncommitted changes that conflict with the remote.
    echo.
    echo To inspect the situation:
    echo     git status
    echo.
    echo To temporarily stash local changes and try again:
    echo     git stash
    echo     update.bat
    echo     git stash pop
    echo.
    pause
    exit /b 1
)
echo [OK]  Source code is up to date.
echo.

:: ---------- 4. Refresh dependencies in the venv ----------
set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PY%" (
    echo [*] Refreshing dependencies inside .venv ...
    "%VENV_PY%" -m pip install --upgrade pip --disable-pip-version-check --quiet
    "%VENV_PY%" -m pip install -r "%~dp0requirements.txt" --upgrade --disable-pip-version-check --quiet
    if errorlevel 1 (
        echo [WARN] Some dependencies failed to update. Run manually:
        echo     "%VENV_PY%" -m pip install -r "%~dp0requirements.txt" --upgrade
    ) else (
        echo [OK]  Dependencies refreshed.
    )
) else (
    echo [INFO] No .venv folder found - skipping dependency update.
    echo        Run run.bat once to create the virtual environment.
)

echo.
echo ============================================
echo  Update complete. Run run.bat to launch.
echo ============================================
pause
endlocal

@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PYTHON=python"
where py >nul 2>nul && set "PYTHON=py -3"

echo ==> Creating virtualenv at .venv
%PYTHON% -m venv .venv
if errorlevel 1 (
  echo Failed to create virtualenv. Install Python 3.10+ and retry.
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .

if not exist .env (
  copy /Y .env.example .env >nul
  echo ==> Wrote .env from .env.example
)

if not exist templates mkdir templates
if not exist output mkdir output
if not exist plugins mkdir plugins

echo ==> Running unit tests
python -m pytest -q
if errorlevel 1 exit /b 1

echo.
echo Setup complete.
echo   Desktop UI:  python main.py
echo   Local LLM:   start LM Studio / Ollama / llama.cpp first
echo   UXP plugin:  load uxp-plugin\ via Adobe UXP Developer Tool
echo   Optional MCP: desain-mcp
exit /b 0

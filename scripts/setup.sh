#!/usr/bin/env bash
# One-command setup for DES.ai.N
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
VENV="${ROOT}/.venv"

echo "==> Creating virtualenv at ${VENV}"
"${PYTHON}" -m venv "${VENV}"
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing dependencies"
python -m pip install -r requirements.txt
python -m pip install -e .

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Wrote .env from .env.example (edit secrets locally)"
fi

mkdir -p templates output plugins

echo "==> Running unit tests"
python -m pytest -q

echo ""
echo "Setup complete."
echo "  Desktop UI:  python main.py"
echo "  Local LLM:   start LM Studio / Ollama / llama.cpp first"
echo "  UXP plugin:  load uxp-plugin/ via Adobe UXP Developer Tool (macOS / cross-platform)"
echo "  Optional MCP: desain-mcp"
echo "  Docs:        docs/setup.md"

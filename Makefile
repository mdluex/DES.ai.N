.PHONY: setup test lint app mcp

setup:
	bash scripts/setup.sh

test:
	DESAIN_BRIDGE_BACKEND=mock pytest -q

lint:
	ruff check desain tests utils

app:
	python main.py

mcp:
	python -m desain.mcp.server

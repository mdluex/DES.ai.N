.PHONY: setup test lint mcp

setup:
	bash scripts/setup.sh

test:
	DESAIN_BRIDGE_BACKEND=mock pytest -q

lint:
	ruff check desain tests utils

mcp:
	python -m desain.mcp.server

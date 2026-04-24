PYTHON=uv run python

.PHONY: install api worker test lint format check

install:
	uv sync

api:
	uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	uv run python -m src.worker.main

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check .
	uv run pytest

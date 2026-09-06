.PHONY: install dev test lint fmt migrate revision up down

install:      ## create venv + install deps
	python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"

dev:          ## run the API with autoreload
	uvicorn app.main:app --reload --port 8000

test:
	pytest -q

lint:
	ruff check . && mypy app

fmt:
	ruff format . && ruff check --fix .

revision:     ## make revision m="add posts table"
	alembic revision --autogenerate -m "$(m)"

migrate:
	alembic upgrade head

up:
	docker compose up --build

down:
	docker compose down -v

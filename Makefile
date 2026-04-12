.PHONY: dev test lint typecheck migrate build

dev:
	docker compose up --build

test:
	cd services/iagent-center && uv run pytest tests/unit tests/integration -v

test-e2e:
	cd services/iagent-center && uv run pytest tests/e2e -v

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy services/iagent-center/src

format:
	uv run ruff format .
	uv run ruff check --fix .

migrate:
	cd services/iagent-center && uv run alembic upgrade head

migrate-new:
	cd services/iagent-center && uv run alembic revision --autogenerate -m "$(name)"

build:
	docker compose build iagent-center

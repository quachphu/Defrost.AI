.PHONY: dev test migrate lint typecheck install up down

# Install the package plus dev tooling into the active environment.
install:
	pip install -e ".[dev]"

# Run the API locally (requires the infra extra + a running stack: see `make up`).
dev:
	uvicorn defrosted.api.app:app --reload --host 0.0.0.0 --port 8000

# Run the test suite.
test:
	pytest -q

# Apply database migrations.
migrate:
	alembic upgrade head

# Lint (zero errors allowed per spec §13).
lint:
	ruff check src tests

# Static type check.
typecheck:
	mypy src

# Bring up local infrastructure (postgres, redis, temporal, elasticsearch).
up:
	docker compose up -d

down:
	docker compose down

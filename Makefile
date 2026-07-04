.PHONY: dev lint typecheck install up down

# Install the package plus dev tooling into the active environment.
install:
	pip install -e ".[infra,dev]"

# Run the API locally (requires postgres: see `make up`).
dev:
	uvicorn defrosted.rent_vs_buy_app:app --reload --host 0.0.0.0 --port 8000

# Lint.
lint:
	ruff check src

# Static type check.
typecheck:
	mypy src

# Bring up the local stack (postgres + app).
up:
	docker compose up -d

down:
	docker compose down

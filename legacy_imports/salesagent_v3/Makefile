.PHONY: help dev test lint docker-up docker-down db-migrate seed seed-synthetic export-dpo

help:
	@echo "SalesAgent V3 — Available Commands"
	@echo "  make docker-up        Start PostgreSQL, Redis, MinIO"
	@echo "  make docker-down      Stop all containers"
	@echo "  make dev              Start FastAPI dev server (hot reload)"
	@echo "  make platform         Start React platform dev server"
	@echo "  make db-migrate       Run Alembic migrations"
	@echo "  make seed             Seed initial prompt templates & strategies"
	@echo "  make seed-synthetic   Generate 100 synthetic training dialogues"
	@echo "  make test             Run all tests"
	@echo "  make lint             Run ruff linter"
	@echo "  make export-dpo       Export DPO preference pairs as JSONL"

docker-up:
	docker compose -f deployment/docker/docker-compose.dev.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	docker compose -f deployment/docker/docker-compose.dev.yml ps

docker-down:
	docker compose -f deployment/docker/docker-compose.dev.yml down

dev:
	poetry run uvicorn salesagent.main:app --reload --host 0.0.0.0 --port 8000

platform:
	cd platform && npm run dev

db-migrate:
	poetry run alembic upgrade head

seed:
	poetry run python scripts/seed_prompts.py

seed-synthetic:
	poetry run python scripts/seed_synthetic_data.py

test:
	poetry run pytest tests/ -v --tb=short --cov=salesagent --cov-report=term-missing

lint:
	poetry run ruff check salesagent/ tests/
	poetry run mypy salesagent/

export-dpo:
	poetry run python scripts/export_dpo_pairs.py

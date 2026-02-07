.PHONY: help setup dev test lint format build deploy clean

help: ## Show this help message
	@echo "SalesBoost Development Commands"
	@echo "================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial project setup
	@echo "Setting up SalesBoost project..."
	pip install -r backend/requirements.txt
	cd frontend && npm install
	@echo "Setup complete!"

dev: ## Start development environment
	@echo "Starting development environment..."
	docker-compose -f deployment/docker/compose.base.yml -f deployment/docker/compose.dev.yml up -d
	@echo "Development environment started!"

dev-backend: ## Start backend development server
	@echo "Starting backend server..."
	cd backend && python main.py

dev-frontend: ## Start frontend development server
	@echo "Starting frontend server..."
	cd frontend && npm run dev

test: ## Run all tests
	@echo "Running tests..."
	cd backend && pytest tests/

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	cd backend && pytest tests/unit/

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	cd backend && pytest tests/integration/

test-e2e: ## Run end-to-end tests
	@echo "Running E2E tests..."
	cd backend && pytest tests/e2e/

lint: ## Run code quality checks
	@echo "Running linters..."
	cd backend && ruff check .
	cd frontend && npm run lint

format: ## Format code
	@echo "Formatting code..."
	cd backend && ruff format .
	cd frontend && npm run format

build: ## Build production images
	@echo "Building production images..."
	docker-compose -f deployment/docker/compose.base.yml -f deployment/docker/compose.prod.yml build

deploy-local: ## Deploy to local environment
	@echo "Deploying to local..."
	./deployment/scripts/deploy-local.sh

deploy-production: ## Deploy to production
	@echo "Deploying to production..."
	./deployment/scripts/deploy-production.sh

deploy-aliyun: ## Deploy to Aliyun
	@echo "Deploying to Aliyun..."
	./deployment/scripts/deploy-cloud-aliyun.sh

clean: ## Clean up temporary files
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache 2>/dev/null || true
	rm -rf frontend/dist 2>/dev/null || true
	rm -rf frontend/node_modules/.cache 2>/dev/null || true
	@echo "Cleanup complete!"

docker-up: ## Start all Docker services
	@echo "Starting Docker services..."
	docker-compose -f deployment/docker/compose.base.yml up -d

docker-down: ## Stop all Docker services
	@echo "Stopping Docker services..."
	docker-compose -f deployment/docker/compose.base.yml down

docker-logs: ## Show Docker logs
	docker-compose -f deployment/docker/compose.base.yml logs -f

docker-ps: ## Show running Docker containers
	docker-compose -f deployment/docker/compose.base.yml ps

install-backend: ## Install backend dependencies
	@echo "Installing backend dependencies..."
	pip install -r backend/requirements.txt

install-frontend: ## Install frontend dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	cd backend && alembic upgrade head

db-rollback: ## Rollback last database migration
	@echo "Rolling back database migration..."
	cd backend && alembic downgrade -1

db-reset: ## Reset database
	@echo "Resetting database..."
	cd backend && alembic downgrade base && alembic upgrade head

check: ## Run all checks (lint + test)
	@echo "Running all checks..."
	$(MAKE) lint
	$(MAKE) test

status: ## Show project status
	@echo "=== Project Status ==="
	@echo ""
	@echo "Git Branch:"
	@git branch --show-current
	@echo ""
	@echo "Git Status:"
	@git status --short
	@echo ""
	@echo "Docker Services:"
	@docker-compose -f deployment/docker/compose.base.yml ps 2>/dev/null || echo "Docker not running"

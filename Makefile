.DEFAULT_GOAL := help

SHELL := /bin/bash
PYTHON ?= python3
NPM ?= npm

.PHONY: help install dev dev-backend dev-frontend test test-backend test-frontend lint lint-backend lint-frontend migrate build clean docker-up docker-down

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies for both frontend and backend
	@echo "==> Installing backend Python dependencies..."
	@if [ -d "apps/api" ]; then cd apps/api && $(PYTHON) -m pip install --upgrade pip && $(PYTHON) -m pip install -r requirements.txt; fi
	@echo "==> Installing frontend Node dependencies..."
	@if [ -d "apps/web" ]; then cd apps/web && $(NPM) install; fi
	@echo "==> Dependencies successfully installed."

dev: docker-up ## Start local infrastructure and development servers
	@echo "==> Local infrastructure started. Run 'make dev-backend' and 'make dev-frontend' in separate terminals, or use your process manager."

dev-backend: ## Run FastAPI backend development server with hot-reload
	@echo "==> Launching FastAPI backend server on http://localhost:8000..."
	@cd apps/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run React/Vite frontend development server
	@echo "==> Launching Vite frontend dev server on http://localhost:5173..."
	@cd apps/web && $(NPM) run dev

test: test-backend test-frontend ## Run test suites for both backend and frontend

test-backend: ## Run backend unit and integration tests with pytest
	@echo "==> Executing backend pytest suite..."
	@cd apps/api && pytest --cov=app --cov-report=term-missing tests/

test-frontend: ## Run frontend unit tests with Vitest
	@echo "==> Executing frontend test suite..."
	@cd apps/web && $(NPM) test -- --run

lint: lint-backend lint-frontend ## Run linters and type checkers for backend and frontend

lint-backend: ## Run Ruff, Black check, and Mypy on backend
	@echo "==> Checking backend with Ruff, Black, and Mypy..."
	@cd apps/api && ruff check . && black --check . && mypy app

lint-frontend: ## Run ESLint, Prettier check, and TypeScript compiler check
	@echo "==> Checking frontend with ESLint, Prettier, and TypeScript..."
	@cd apps/web && $(NPM) run lint && $(NPM) run type-check

migrate: ## Apply database migrations using Supabase CLI / Alembic
	@echo "==> Applying database migrations..."
	@if [ -d "packages/database" ]; then cd packages/database && npx supabase db push; \
	elif [ -d "apps/api" ]; then cd apps/api && alembic upgrade head; fi

build: ## Build both frontend and backend for production
	@echo "==> Building frontend distribution assets..."
	@cd apps/web && $(NPM) run build
	@echo "==> Frontend build completed. Backend is interpreted Python (ready for container packaging)."

docker-up: ## Start PostgreSQL, Redis, and pgAdmin containers
	@echo "==> Starting Docker Compose services (Postgres, Redis, pgAdmin)..."
	docker compose up -d

docker-down: ## Stop all Docker Compose services
	@echo "==> Stopping Docker Compose services..."
	docker compose down

clean: ## Clean build artifacts, caches, and temporary files
	@echo "==> Cleaning cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune -o -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf apps/web/dist apps/api/.coverage apps/api/htmlcov
	@echo "==> Clean complete."

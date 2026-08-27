# Canonical commands for Cursor/Codex. Run from the repository root.

PYTHON ?= python3
BACKEND_DIR := backend
FRONTEND_DIR := frontend
NPM ?= npm

COMPOSE ?= docker compose

.PHONY: help backend-install backend-lint backend-format backend-typecheck backend-test backend-check backend-run \
	frontend-install frontend-lint frontend-typecheck frontend-test frontend-build frontend-check frontend-run \
	compose-config compose-up compose-down compose-ps

help:
	@echo "neuroTrade canonical commands"
	@echo "  make backend-install      Install backend runtime + dev extras"
	@echo "  make backend-lint         Ruff lint + format check"
	@echo "  make backend-format       Ruff autofix/format"
	@echo "  make backend-typecheck    mypy on backend/app"
	@echo "  make backend-test         pytest"
	@echo "  make backend-check        lint + typecheck + tests"
	@echo "  make backend-run          uvicorn control plane on :8000"
	@echo "  make frontend-install     npm install in frontend/"
	@echo "  make frontend-lint        next lint"
	@echo "  make frontend-typecheck   tsc --noEmit"
	@echo "  make frontend-test        vitest run"
	@echo "  make frontend-build       next build"
	@echo "  make frontend-check       lint + typecheck + tests + build"
	@echo "  make frontend-run         next dev on :3000"
	@echo "  make compose-config      Validate docker-compose.yml"
	@echo "  make compose-up          docker compose up --build -d (PAPER)"
	@echo "  make compose-down        docker compose down"
	@echo "  make compose-ps          docker compose ps"
	@echo "GitHub Actions runs make backend-check and make frontend-check (PAPER)."

backend-install:
	$(PYTHON) -m pip install -e "$(BACKEND_DIR)[dev]"

backend-lint:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check .
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff format --check .

backend-format:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff format .
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check --fix .

backend-typecheck:
	cd $(BACKEND_DIR) && $(PYTHON) -m mypy app

backend-test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest

backend-check: backend-lint backend-typecheck backend-test

backend-run:
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

frontend-install:
	cd $(FRONTEND_DIR) && $(NPM) install

frontend-lint:
	cd $(FRONTEND_DIR) && $(NPM) run lint

frontend-typecheck:
	cd $(FRONTEND_DIR) && $(NPM) run typecheck

frontend-test:
	cd $(FRONTEND_DIR) && $(NPM) run test

frontend-build:
	cd $(FRONTEND_DIR) && $(NPM) run build

frontend-check: frontend-lint frontend-typecheck frontend-test frontend-build

frontend-run:
	cd $(FRONTEND_DIR) && $(NPM) run dev

compose-config:
	$(COMPOSE) -f docker-compose.yml config

compose-up:
	$(COMPOSE) -f docker-compose.yml up --build -d

compose-down:
	$(COMPOSE) -f docker-compose.yml down

compose-ps:
	$(COMPOSE) -f docker-compose.yml ps

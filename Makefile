# Canonical commands for Cursor/Codex. Run from the repository root.
# Frontend/Docker/CI targets will be added when those Phase 0 pieces exist.

PYTHON ?= python3
BACKEND_DIR := backend

.PHONY: help backend-install backend-lint backend-format backend-typecheck backend-test backend-check backend-run

help:
	@echo "neuroTrade canonical commands"
	@echo "  make backend-install     Install backend runtime + dev extras"
	@echo "  make backend-lint        Ruff lint + format check"
	@echo "  make backend-format      Ruff autofix/format"
	@echo "  make backend-typecheck   mypy on backend/app"
	@echo "  make backend-test        pytest"
	@echo "  make backend-check       lint + typecheck + tests"
	@echo "  make backend-run         uvicorn control plane on :8000"

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

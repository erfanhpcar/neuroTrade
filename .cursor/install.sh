#!/usr/bin/env bash
# Idempotent repository bootstrap for the Cloud Agent environment.
# Installs system services (PostgreSQL, Redis) and project dependencies.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Installing system packages (postgresql, redis-server, python venv)"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  postgresql postgresql-contrib \
  redis-server \
  python3-venv

echo "==> Setting up backend virtualenv and dependencies"
cd "$REPO_ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -e ".[dev]"

echo "==> Installing frontend dependencies"
cd "$REPO_ROOT/frontend"
npm install

echo "==> Install complete"

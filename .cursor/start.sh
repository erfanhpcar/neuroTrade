#!/usr/bin/env bash
# Per-boot startup: bring up PostgreSQL and Redis and ensure the app role/database
# exist. Idempotent and safe to run repeatedly. Application processes themselves
# run as terminals (see .cursor/environment.json).
set -euo pipefail

DB_USER="neurotrade"
DB_PASSWORD="neurotrade"
DB_NAME="neurotrade"

echo "==> Starting PostgreSQL"
PG_VERSION="$(ls /etc/postgresql 2>/dev/null | sort -n | tail -1 || true)"
if [ -n "${PG_VERSION}" ]; then
  sudo pg_ctlcluster "${PG_VERSION}" main start 2>/dev/null || true
fi

echo "==> Waiting for PostgreSQL to accept connections"
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then
    break
  fi
  sleep 1
done

echo "==> Ensuring application role and database exist"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

echo "==> Starting Redis"
if redis-cli ping >/dev/null 2>&1; then
  echo "Redis already running"
else
  redis-server --daemonize yes
fi

echo "==> Startup complete"

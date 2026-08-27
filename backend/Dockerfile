# neuroTrade backend image — shared by the FastAPI control plane and the
# trading worker (same codebase, different command; see docker-compose.yml).
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY app ./app

EXPOSE 8000

# Default command runs the control plane. The trading-worker service overrides
# this with: python -m app.workers.trading_worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

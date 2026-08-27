# Shared image for the FastAPI control plane and the trading-worker process.
# Compose overrides the command for trading-worker. Default TRADING_MODE is PAPER.
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=development \
    TRADING_MODE=PAPER \
    LOG_LEVEL=INFO

WORKDIR /app

RUN useradd --create-home --uid 1000 neurotrade

COPY pyproject.toml AGENTS.md alembic.ini ./
COPY app ./app
COPY alembic ./alembic

RUN pip install --upgrade pip \
    && pip install . \
    && rm -rf /root/.cache/pip

USER neurotrade
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"

# Control-plane default. trading-worker overrides this in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

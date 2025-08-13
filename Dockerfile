# ---- Base Python + uv ----
FROM python:3.12-slim AS base

ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=$SETUPTOOLS_SCM_PRETEND_VERSION
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache

RUN apt-get update && \
    apt-get install -y curl build-essential git && \
    curl -Ls https://astral.sh/uv/install.sh | sh && \
    export PATH="/root/.local/bin:$PATH" && \
    uv venv $VIRTUAL_ENV && \
    rm -rf /var/lib/apt/lists/*

# ---- Установка зависимостей Python + Node ----
FROM base AS deps

WORKDIR /app

ENV PATH="/root/.local/bin:$PATH"

# Python deps
COPY pyproject.toml .
COPY version.txt .
COPY README.md .
COPY app ./app

RUN uv pip install .


# ---- Финальный образ ----
FROM base AS final

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Копируем виртуальное окружение и node_modules
COPY --from=deps /app/.venv /app/.venv


# Копируем всё приложение
COPY --chown=appuser:appgroup . /app

RUN mkdir -p /app/fsm-storage && \
    mkdir -p /app/logs && \
    mkdir -p /app/imgs && \
    chown -R appuser:appgroup /app/fsm-storage /app/logs /app/imgs

USER appuser

EXPOSE 53100

CMD ["sh", "-c", "gunicorn run:app -c /app/gunicorn.conf.py"]

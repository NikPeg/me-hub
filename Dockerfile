# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.12.21 AS uv

FROM python:3.14-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.14-slim
RUN useradd --system --uid 10001 --home-dir /app --no-create-home app \
    && mkdir -p /app/data \
    && chown app:app /app/data
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite+aiosqlite:////app/data/me_hub.db
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
USER app
VOLUME ["/app/data"]
CMD ["alembic", "upgrade", "head"]

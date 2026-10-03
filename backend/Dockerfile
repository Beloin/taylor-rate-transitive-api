FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Install the project itself so uv run is fully offline at runtime
RUN uv sync --no-dev --frozen

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000 8443

ENTRYPOINT ["/entrypoint.sh"]
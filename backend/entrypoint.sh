#!/bin/sh
set -e

CERT_DIR="${CERT_DIR:-/certs}"
mkdir -p "$CERT_DIR"

echo "Running migrations..."
uv run --offline --no-dev alembic upgrade head

echo "Starting API (http + https)..."
exec uv run --offline --no-dev python -m app
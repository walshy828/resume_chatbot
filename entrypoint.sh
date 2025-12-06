#!/bin/bash
set -e

echo "=== Running Bootstrap DB Migration ==="
python scripts/bootstrap_migrate.py || true

echo "=== Running Flask-Migrate (Alembic) ==="
export FLASK_APP=app.api
if [ -d "migrations" ]; then
    flask db upgrade || true
else
    echo "No migrations directory found. Skipping flask db upgrade."
fi

echo "=== Starting Application ==="
exec python -m app
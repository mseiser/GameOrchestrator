#!/bin/sh
set -e

if [ -n "$DB_PATH" ]; then
    db_dir=$(dirname "$DB_PATH")
    if [ ! -d "$db_dir" ]; then
        mkdir -p "$db_dir"
    fi

    echo "Ensuring database schema at $DB_PATH..."
    python db/database_setup.py
else
    echo "DB_PATH is not set. Skipping database setup."
fi

# Measurements DB — created automatically by MeasurementManager on first use,
# but we ensure the directory exists here so startup logs are clean.
MEASUREMENTS_DB_PATH="${MEASUREMENTS_DB_PATH:-/data/physicsquest_measurements.db}"
measurements_db_dir=$(dirname "$MEASUREMENTS_DB_PATH")
if [ ! -d "$measurements_db_dir" ]; then
    mkdir -p "$measurements_db_dir"
fi
echo "Measurements DB path: $MEASUREMENTS_DB_PATH"

# Start API on internal port (TLS handled by Caddy reverse proxy)
echo "Starting API on port 8000"
exec python -m uvicorn api:app --host 0.0.0.0 --port 8000 --log-level info
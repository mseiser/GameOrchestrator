#!/bin/sh
set -e

if [ -n "$DB_PATH" ]; then
    db_dir=$(dirname "$DB_PATH")
    if [ ! -d "$db_dir" ]; then
        mkdir -p "$db_dir"
    fi

    if [ ! -f "$DB_PATH" ]; then
        echo "Database not found at $DB_PATH. Creating..."
        python db/database_setup.py
    fi
else
    echo "DB_PATH is not set. Skipping database setup."
fi

exec python -m uvicorn api:app --host 0.0.0.0 --port 8000

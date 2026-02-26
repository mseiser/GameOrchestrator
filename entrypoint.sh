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

if [ -z "$SSL_CERTFILE" ] || [ -z "$SSL_KEYFILE" ]; then
    echo "TLS is required. Set both SSL_CERTFILE and SSL_KEYFILE."
    exit 1
fi

echo "Starting API with TLS enabled"
exec python -m uvicorn api:app --host 0.0.0.0 --port 8000 --ssl-certfile "$SSL_CERTFILE" --ssl-keyfile "$SSL_KEYFILE"

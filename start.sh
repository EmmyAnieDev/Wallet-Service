#!/bin/bash
set -e

APP_PORT=${APP_PORT:-8000}

echo "Starting Wallet Service API on port $APP_PORT..."

if [ "$DEBUG" = "True" ]; then
    echo "Running in DEBUG mode with auto-reload"
    exec uvicorn main:app \
        --host 0.0.0.0 \
        --port "$APP_PORT" \
        --reload \
        --reload-exclude "logs/*" \
        --reload-exclude "*.log" \
        --reload-exclude "__pycache__/*"
else
    echo "Running in PRODUCTION mode"
    exec uvicorn main:app \
        --host 0.0.0.0 \
        --port "$APP_PORT" \
        --workers 1
fi

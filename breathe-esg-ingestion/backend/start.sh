#!/bin/bash
set -e

# Railway injects PORT — fallback to 8000 for safety
export PORT="${PORT:-8000}"
echo "=== PORT: $PORT ==="

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Starting gunicorn on 0.0.0.0:$PORT ==="
exec gunicorn backend.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers 1 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -

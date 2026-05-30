#!/bin/bash
set -e

export PORT="${PORT:-8000}"
echo "=== PORT: $PORT ==="

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Seeding initial data ==="
python manage.py seed_esg_data

echo "=== Starting gunicorn on 0.0.0.0:$PORT ==="
exec gunicorn backend.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers 1 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -

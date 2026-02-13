#!/bin/bash

set -e

echo "Waiting for PostgreSQL to be ready..."

while ! python -c "
import socket
import os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((os.environ.get('POSTGRES_HOST', 'db'), int(os.environ.get('POSTGRES_PORT', 5432))))
    s.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping..."
    sleep 1
done

echo "PostgreSQL is up!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -

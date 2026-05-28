#!/bin/sh
set -e

# Replace placeholder with actual BACKEND_URL env var
BACKEND="${BACKEND_URL:-http://localhost:8000}"
echo "Proxying /api/ to: $BACKEND"

sed "s|BACKEND_URL_PLACEHOLDER|${BACKEND}|g" \
    /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

# Start nginx in foreground
exec nginx -g "daemon off;"

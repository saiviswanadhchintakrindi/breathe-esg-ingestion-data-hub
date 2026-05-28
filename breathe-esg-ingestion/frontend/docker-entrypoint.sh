#!/bin/sh
set -e

# BACKEND_URL should be the Railway internal URL:
# http://<backend-service-name>.railway.internal:<PORT>
# e.g. http://backend.railway.internal:8000
BACKEND="${BACKEND_URL:-http://localhost:8000}"

# Strip trailing slash
BACKEND="${BACKEND%/}"

echo "=== Proxying /api/ to: $BACKEND ==="

sed -e "s|BACKEND_URL_PLACEHOLDER|${BACKEND}|g" \
    /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

echo "=== Final nginx config ==="
cat /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"

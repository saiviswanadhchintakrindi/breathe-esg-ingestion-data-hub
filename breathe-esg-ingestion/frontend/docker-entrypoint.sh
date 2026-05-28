#!/bin/sh
set -e

# Ensure BACKEND_URL has http:// or https:// scheme
BACKEND="${BACKEND_URL:-http://localhost:8000}"
case "$BACKEND" in
  http://*|https://*) ;;
  *) BACKEND="http://$BACKEND" ;;
esac

# Strip trailing slash
BACKEND="${BACKEND%/}"

echo "=== BACKEND_URL resolved to: $BACKEND ==="

# Railway sets PORT dynamically
APP_PORT="${PORT:-3000}"
echo "=== Nginx will listen on port: $APP_PORT ==="

# Substitute placeholders into nginx config
sed \
  -e "s|BACKEND_URL_PLACEHOLDER|${BACKEND}|g" \
  -e "s|PORT_PLACEHOLDER|${APP_PORT}|g" \
  /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

echo "=== Final nginx config: ==="
cat /etc/nginx/conf.d/default.conf

echo "=== Starting nginx... ==="
exec nginx -g "daemon off;"


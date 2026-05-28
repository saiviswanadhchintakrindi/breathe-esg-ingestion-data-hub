#!/bin/sh
set -e

# Railway assigns PORT dynamically — must listen on it
APP_PORT="${PORT:-3000}"
echo "=== Nginx listening on port: $APP_PORT ==="

# Ensure BACKEND_URL has a scheme
BACKEND="${BACKEND_URL:-http://localhost:8000}"
case "$BACKEND" in
  http://*|https://*) ;;
  *) BACKEND="http://$BACKEND" ;;
esac
BACKEND="${BACKEND%/}"
echo "=== Proxying /api/ to: $BACKEND ==="

# Substitute both placeholders
sed \
  -e "s|PORT_PLACEHOLDER|${APP_PORT}|g" \
  -e "s|BACKEND_URL_PLACEHOLDER|${BACKEND}|g" \
  /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

echo "=== Final nginx config ==="
cat /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"

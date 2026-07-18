#!/usr/bin/env bash
set -euo pipefail

WEB_BASE_URL="${WEB_BASE_URL:-http://127.0.0.1:3000}"

if [[ "${PUBLIC_DEMO_ACK:-}" != "I_UNDERSTAND" ]]; then
  echo "Refusing to create a public tunnel without PUBLIC_DEMO_ACK=I_UNDERSTAND."
  echo "The link exposes the login page to the internet while this process is running."
  exit 2
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is required. Install it before starting a temporary demo tunnel."
  exit 2
fi

if ! curl -fsS "${WEB_BASE_URL}/login" >/dev/null; then
  echo "The web app is not reachable at ${WEB_BASE_URL}."
  echo "Start the Docker stack first with: docker compose up -d"
  exit 1
fi

echo "Starting a temporary HTTPS tunnel for ${WEB_BASE_URL}."
echo "Only the web entry point is exposed; keep this terminal running during the demo."
echo "Stop the tunnel with Ctrl-C when access is no longer needed."

exec cloudflared tunnel \
  --url "${WEB_BASE_URL}" \
  --protocol http2 \
  --no-autoupdate

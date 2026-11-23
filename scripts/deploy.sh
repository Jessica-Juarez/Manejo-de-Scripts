#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

bash "$SCRIPT_DIR/setup-release.sh"
APP_PORT="$(sed -n 's/^APP_PORT=//p' .env | tail -n 1)"

docker compose config --quiet
docker compose up -d --build --remove-orphans

for attempt in $(seq 1 30); do
  if curl --fail --silent "http://127.0.0.1:$APP_PORT/healthz" >/dev/null; then
    echo "Despliegue listo: http://127.0.0.1:$APP_PORT"
    exit 0
  fi
  sleep 1
done

echo "Error: la aplicación no respondió correctamente a /healthz." >&2
docker compose logs --tail=80
exit 1

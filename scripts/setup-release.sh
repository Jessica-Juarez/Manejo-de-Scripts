#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: instala Docker Engine antes de preparar el entorno." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Error: instala el complemento Docker Compose v2." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: instala curl para comprobar la salud del despliegue." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: el usuario actual no puede conectarse a Docker." >&2
  exit 1
fi

if [ ! -f .env ]; then
  printf 'APP_PORT=8080\n' > .env
fi

if ! grep -q '^APP_PORT=' .env; then
  printf 'APP_PORT=8080\n' >> .env
fi

APP_PORT="$(sed -n 's/^APP_PORT=//p' .env | tail -n 1)"
case "$APP_PORT" in
  ''|*[!0-9]*)
    echo "Error: APP_PORT en .env debe ser un puerto numérico." >&2
    exit 1
    ;;
esac

if [ "$APP_PORT" -lt 1 ] || [ "$APP_PORT" -gt 65535 ]; then
  echo "Error: APP_PORT debe estar entre 1 y 65535." >&2
  exit 1
fi

echo "Entorno de liberación listo (APP_PORT=$APP_PORT)."

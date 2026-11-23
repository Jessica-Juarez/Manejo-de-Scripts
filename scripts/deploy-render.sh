#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${RENDER_DEPLOY_HOOK_URL:-}" ]]; then
  echo "Error: configura el secret RENDER_DEPLOY_HOOK_URL en el entorno production de GitHub." >&2
  exit 1
fi

if [[ ! "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Error: GITHUB_SHA debe identificar el commit validado." >&2
  exit 1
fi

if ! status="$(curl --silent --show-error --max-time 30 --output /dev/null \
  --write-out '%{http_code}' --get --data-urlencode "ref=$GITHUB_SHA" \
  "$RENDER_DEPLOY_HOOK_URL")"; then
  echo "Error: no se pudo conectar con Render." >&2
  exit 1
fi

case "$status" in
  200) echo "Render inició el despliegue; revisa su resultado en el panel de Render." ;;
  202) echo "Render puso el despliegue en espera; revisa su resultado en el panel de Render." ;;
  *) echo "Error: Render rechazó la solicitud de despliegue (HTTP $status)." >&2; exit 1 ;;
esac

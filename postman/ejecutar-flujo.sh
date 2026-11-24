#!/usr/bin/env bash
# Ejecuta el flujo de la demo de la colección con Newman: cliente → firma y siniestro → Operaciones.
#
# Uso:
#   ADMIN_PASSWORD='...' BACKEND_LOG=/tmp/backend.log ./postman/ejecutar-flujo.sh local
#   ADMIN_PASSWORD='...' LOG_GROUP=<grupo-de-logs> BASE_URL=https://<cloudfront> ./postman/ejecutar-flujo.sh aws
#
# El OTP de la firma se lee del log del backend: archivo local (BACKEND_LOG) o CloudWatch (LOG_GROUP).
# Con REPORTES=<carpeta> se guarda además un reporte HTML por fase (requiere newman-reporter-htmlextra).
set -euo pipefail

AMBIENTE="${1:-local}"
DIR="$(cd "$(dirname "$0")" && pwd)"
COLECCION="$DIR/Solventa.postman_collection.json"
case "$AMBIENTE" in
  local) ARCHIVO_AMBIENTE="$DIR/Solventa-local.postman_environment.json" ;;
  aws) ARCHIVO_AMBIENTE="$DIR/Solventa-AWS.postman_environment.json" ;;
  *) echo "Ambiente desconocido: $AMBIENTE (use local o aws)"; exit 1 ;;
esac

: "${ADMIN_PASSWORD:?Defina ADMIN_PASSWORD (usuario SERVICIO_INTERNO)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if command -v newman > /dev/null; then
  NEWMAN=(newman run "$COLECCION")
else
  NEWMAN=(npx --yes newman@6 run "$COLECCION")
fi
EXTRA=(--env-var "admin_password=$ADMIN_PASSWORD")
[ -n "${BASE_URL:-}" ] && EXTRA+=(--env-var "baseUrl=$BASE_URL")
[ -n "${ADMIN_EMAIL:-}" ] && EXTRA+=(--env-var "admin_email=$ADMIN_EMAIL")

# Reporte HTML de una fase. skipSensitiveData quita encabezados y cuerpos (contraseñas, tokens) y se
# ocultan las variables del ambiente con credenciales, porque el reporte se publica como artefacto.
REP=()
reporte() {
  REP=()
  [ -z "${REPORTES:-}" ] && return 0
  mkdir -p "$REPORTES"
  REP=(-r cli,htmlextra --reporter-htmlextra-export "$REPORTES/$1.html"
    --reporter-htmlextra-skipSensitiveData
    --reporter-htmlextra-skipEnvironmentVars "token,admin_token,operaciones_token,admin_password,cliente_password,operaciones_password,otp"
    --reporter-htmlextra-title "Solventa API · $AMBIENTE · $1")
}

valor() { node -e "const e=require('$1');console.log((e.values.find(v=>v.key==='$2')||{}).value||'')"; }

leer_otp() {
  local firma="$1" logs=""
  for _ in $(seq 1 10); do
    if [ -n "${LOG_GROUP:-}" ]; then
      logs="$(aws logs filter-log-events --log-group-name "$LOG_GROUP" --filter-pattern "\"$firma\"" \
        --start-time $(( ($(date +%s) - 600) * 1000 )) --query 'events[].message' --output text)"
    elif [ -n "${BACKEND_LOG:-}" ]; then
      logs="$(cat "$BACKEND_LOG")"
    else
      echo "Defina BACKEND_LOG o LOG_GROUP para leer el OTP" >&2; return 1
    fi
    local otp
    otp="$(grep -oE "OTP [0-9]{6} .*\(proceso $firma\)" <<<"$logs" | tail -1 | grep -oE '[0-9]{6}' | head -1 || true)"
    if [ -n "$otp" ]; then echo "$otp"; return 0; fi
    sleep 2
  done
  echo "No se encontró el OTP del proceso $firma" >&2; return 1
}

echo "== 1. Cliente: registro, cotización y pago"
reporte 1-cliente
"${NEWMAN[@]}" -e "$ARCHIVO_AMBIENTE" "${EXTRA[@]}" --folder "1. Cliente: registro, cotización y pago" \
  --export-environment "$TMP/1.json" ${REP[@]+"${REP[@]}"}

OTP="$(leer_otp "$(valor "$TMP/1.json" firma_id)")"
echo "== 2. Firma, póliza y siniestro (OTP leído del log)"
reporte 2-firma-siniestro
"${NEWMAN[@]}" -e "$TMP/1.json" --env-var "otp=$OTP" --folder "2. Firma, póliza y siniestro" \
  --export-environment "$TMP/2.json" ${REP[@]+"${REP[@]}"}

echo "== 3. Operaciones: aprobar el siniestro"
reporte 3-operaciones
"${NEWMAN[@]}" -e "$TMP/2.json" --folder "3. Operaciones: aprobar el siniestro" ${REP[@]+"${REP[@]}"}

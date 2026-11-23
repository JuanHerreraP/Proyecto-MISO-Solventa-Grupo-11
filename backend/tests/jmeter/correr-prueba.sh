#!/usr/bin/env bash
# Ejecuta la prueba de carga de telemetría contra el despliegue y, al terminar,
# concilia los eventos: enviados (JMeter) vs aceptados (202) vs en cola vs en DLQ vs
# procesados en BD. Demuestra que no se pierde ningún evento aceptado.
#
# Uso (empieza pequeño y sube):
#   bash backend/tests/jmeter/correr-prueba.sh                 # 60s, ritmo moderado (humo)
#   HILOS=400 DURACION_SEG=600 THROUGHPUT_POR_MIN=100020 \
#     bash backend/tests/jmeter/correr-prueba.sh               # objetivo 1M/10min
#
# Variables:
#   JMETER_BIN   ruta a jmeter (si no, se busca en PATH y en ~/herramientas)
#   HILOS, DURACION_SEG, THROUGHPUT_POR_MIN  parámetros de carga
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
STACK="${STACK:-solventa-mvp}"
API_KEY="${API_KEY:-solventa-telemetry-dev}"
HILOS="${HILOS:-50}"
DURACION_SEG="${DURACION_SEG:-60}"
THROUGHPUT_POR_MIN="${THROUGHPUT_POR_MIN:-6000}"

cd "$(git rev-parse --show-toplevel)"
JMX="backend/tests/jmeter/telemetria_1M.jmx"

# Localizar jmeter
JMETER_BIN="${JMETER_BIN:-$(command -v jmeter || true)}"
if [ -z "$JMETER_BIN" ]; then
  CAND=$(ls -d "$HOME"/herramientas/apache-jmeter-*/bin/jmeter 2>/dev/null | head -1 || true)
  JMETER_BIN="$CAND"
fi
if [ -z "$JMETER_BIN" ] || [ ! -x "$JMETER_BIN" ]; then
  echo "ERROR: no encuentro jmeter. Corre primero: bash backend/tests/jmeter/instalar-jmeter.sh" >&2
  exit 1
fi

echo ">> Descubriendo URL, cola y DLQ del stack ..."
BASE_URL=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Url'].OutputValue" --output text)
QUEUE_URL=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='QueueUrl'].OutputValue" --output text)
DLQ_URL=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='DlqUrl'].OutputValue" --output text)
echo "   BASE_URL=$BASE_URL"
echo "   QUEUE_URL=$QUEUE_URL"

SELLO="$(date -u +%Y%m%d-%H%M%S)"
SALIDA="backend/tests/jmeter/salidas/$SELLO"
mkdir -p "$SALIDA"
JTL="$SALIDA/resultados.jtl"

echo
echo ">> Lanzando JMeter: HILOS=$HILOS DURACION=${DURACION_SEG}s RITMO=${THROUGHPUT_POR_MIN}/min"
"$JMETER_BIN" -n -t "$JMX" -l "$JTL" -e -o "$SALIDA/reporte" \
  -JBASE_URL="$BASE_URL" \
  -JAPI_KEY="$API_KEY" \
  -JHILOS="$HILOS" \
  -JDURACION_SEG="$DURACION_SEG" \
  -JTHROUGHPUT_POR_MIN="$THROUGHPUT_POR_MIN"

echo
echo ">> Resumen de JMeter (desde el .jtl):"
python3 - "$JTL" <<'PY'
import csv, sys
total=exitos=cod202=cod200=otros=0
codes={}
with open(sys.argv[1]) as f:
    for row in csv.DictReader(f):
        total+=1
        c=row.get("responseCode","")
        codes[c]=codes.get(c,0)+1
        if row.get("success")=="true": exitos+=1
        if c=="202": cod202+=1
        elif c=="200": cod200+=1
        else: otros+=1
print(f"   Enviados (samples):     {total}")
print(f"   Aceptados (success):    {exitos}")
print(f"   HTTP 202 (encolados):   {cod202}")
print(f"   HTTP 200 (sincrono):    {cod200}")
print(f"   Otros/errores:          {total-cod202-cod200}")
print(f"   Desglose por codigo:    {codes}")
ACEPTADOS=cod202+cod200
open("/tmp/ec_aceptados","w").write(str(ACEPTADOS))
print(f"   >> ACEPTADOS = {ACEPTADOS}")
PY
ACEPTADOS=$(cat /tmp/ec_aceptados 2>/dev/null || echo 0)

echo
echo ">> Estado de la cola (puede seguir drenando: espera y repite si hace falta):"
aws sqs get-queue-attributes --queue-url "$QUEUE_URL" \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
  --query "Attributes" --output json
echo ">> Estado de la DLQ:"
aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages \
  --query "Attributes" --output json

echo
echo ">> Reporte HTML: $SALIDA/reporte/index.html"
echo ">> Para conciliar contra la BD (cuando la cola llegue a 0), corre la tarea ECS de conciliacion"
echo "   con ACEPTADOS=$ACEPTADOS (ver docs/ec-contrapresion-telemetria.md)."

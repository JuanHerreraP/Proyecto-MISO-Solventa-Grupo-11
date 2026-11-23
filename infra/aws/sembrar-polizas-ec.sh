#!/usr/bin/env bash
# Siembra pólizas paramétricas para el EC de telemetría (HU20) ejecutando un script
# Python EN LÍNEA como tarea ECS puntual en la red privada (con acceso a RDS).
#
# No requiere reconstruir la imagen: reutiliza la task definition del servicio y
# solo sobreescribe el comando del contenedor "backend". El script inline usa los
# modelos que ya viven dentro de app/ en la imagen desplegada.
#
# Crea 3 pólizas PARAMETRICAS vigentes para el cliente CLIENTE_EMAIL:
#   - EVENTO_CLIMATICO / ubicacion=BOG   / umbral 180
#   - RETRASO_VUELO    / numero_vuelo=AV100 / umbral 180
#   - EVENTO_CLIMATICO / ubicacion=MED   / umbral 100
# Es idempotente (repetirlo actualiza las mismas pólizas por su poliza_id).
#
# Uso:
#   AWS_REGION=us-east-1 STACK=solventa-mvp CLIENTE_EMAIL=ana.ec.prueba@gmail.com \
#   ./infra/aws/sembrar-polizas-ec.sh
set -euo pipefail

: "${AWS_REGION:?Define AWS_REGION}"
: "${STACK:=solventa-mvp}"
: "${CLIENTE_EMAIL:?Define CLIENTE_EMAIL}"
export AWS_DEFAULT_REGION="$AWS_REGION"

echo "Descubriendo recursos del stack $STACK ..."
CLUSTER=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Cluster'].OutputValue" --output text)
SERVICE=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Service'].OutputValue" --output text)
TASKDEF=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query "services[0].taskDefinition" --output text)
read -r SUBNETS SGS <<<"$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query "services[0].networkConfiguration.awsvpcConfiguration.[join(',',subnets),join(',',securityGroups)]" \
  --output text)"

echo "Cluster:  $CLUSTER"
echo "TaskDef:  $TASKDEF"
echo "Subnets:  $SUBNETS"
echo "SG:       $SGS"

# Script Python inline. Siembra las pólizas paramétricas para el cliente dado.
PYCODE='
import os, secrets
from urllib.parse import quote
# Reproduce lo que hace entrypoint.py: construye DATABASE_URL desde DB_HOST/DB_PASSWORD,
# porque este comando no pasa por el entrypoint.
if os.environ.get("DB_HOST") and not os.environ.get("DATABASE_URL"):
    _h = os.environ.get("DB_HOST")
    _u = quote(os.environ.get("DB_USER", "solventa"), safe="")
    _p = quote(os.environ.get("DB_PASSWORD", ""), safe="")
    os.environ["DATABASE_URL"] = f"postgresql+psycopg://{_u}:{_p}@{_h}:5432/solventa?sslmode=require"
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from app.identidad.modelos_db import UsuarioDB
from app.infraestructura.database import Base, SessionLocal, engine, esperar_base_disponible
from app.polizas import modelos_db  # noqa
from app.polizas.dominio.modelos import (
    CoberturaPoliza, EstadoRegistroPoliza, Poliza, RamoPoliza, hoy_en_colombia,
)
from app.polizas.repositorio import RepositorioPolizasPostgres

email = os.environ["CLIENTE_EMAIL"].strip().lower()
esperar_base_disponible()
Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    u = db.scalar(select(UsuarioDB).where(UsuarioDB.email == email))
    if u is None:
        raise SystemExit(f"ERROR: no existe cliente {email}")
    if u.rol != "CLIENTE":
        raise SystemExit(f"ERROR: {email} no es CLIENTE (rol {u.rol})")
    sufijo = str(u.id).replace("-", "")[:8].upper()
    hoy = hoy_en_colombia(datetime.now(UTC))
    emitida = datetime.now(UTC)
    repo = RepositorioPolizasPostgres(db)
    defs = [
        ("EC-CLIMA-BOG", "tipo_evento=EVENTO_CLIMATICO; ubicacion=BOG; umbral_disparo=180; unidad=MINUTOS", "Evento climatico BOG"),
        ("EC-VUELO-AV100", "tipo_evento=RETRASO_VUELO; numero_vuelo=AV100; ubicacion=BOG; umbral_disparo=180; unidad=MINUTOS", "Retraso vuelo AV100"),
        ("EC-CLIMA-MED", "tipo_evento=EVENTO_CLIMATICO; ubicacion=MED; umbral_disparo=100; unidad=MINUTOS", "Evento climatico MED"),
    ]
    for n, cond, nombre in defs:
        p = Poliza(
            poliza_id=f"EC-{sufijo}-{n}",
            numero_poliza=f"SOL-PM-{sufijo}-{n}"[:40],
            cliente_id=str(u.id),
            ramo=RamoPoliza.PARAMETRICO,
            estado=EstadoRegistroPoliza.VIGENTE,
            titular_nombre=f"{u.nombre} {u.apellido}",
            titular_tipo_documento=u.tipo_documento,
            titular_numero_documento=u.numero_documento,
            fecha_inicio=hoy - timedelta(days=10),
            fecha_fin=hoy + timedelta(days=60),
            prima_total=Decimal("45000.00"),
            cobertura_principal=CoberturaPoliza(
                codigo="PARAMETRICO_EC",
                nombre=nombre,
                suma_asegurada=Decimal("500000.00"),
                descripcion=cond,
            ),
            codigo_verificacion=secrets.token_hex(8),
            emitida_en=emitida,
        )
        repo.guardar(p)
        print(f"OK {p.poliza_id}  {cond}")
    print("Siembra EC completa.")
finally:
    db.close()
'

OVERRIDES=$(python3 - "$PYCODE" "$CLIENTE_EMAIL" <<'JSON'
import json, sys
pycode, cliente = sys.argv[1], sys.argv[2]
print(json.dumps({
    "containerOverrides": [{
        "name": "backend",
        "command": ["python", "-c", pycode],
        "environment": [{"name": "CLIENTE_EMAIL", "value": cliente}],
    }]
}))
JSON
)

NET="awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${SGS}],assignPublicIp=DISABLED}"

echo "Lanzando tarea de siembra ..."
TASK_ARN=$(aws ecs run-task \
  --cluster "$CLUSTER" \
  --task-definition "$TASKDEF" \
  --launch-type FARGATE \
  --platform-version 1.4.0 \
  --network-configuration "$NET" \
  --overrides "$OVERRIDES" \
  --query "tasks[0].taskArn" --output text)

echo "Tarea: $TASK_ARN"
echo "Esperando a que termine ..."
aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK_ARN"

EXIT=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query "tasks[0].containers[?name=='backend'].exitCode | [0]" --output text)
REASON=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query "tasks[0].stoppedReason" --output text)

echo "Exit code: $EXIT"
echo "Motivo de parada: $REASON"
echo "Detalle en el log group del stack (prefijo de stream: backend)."
if [ "$EXIT" != "0" ]; then
  echo "La siembra no terminó con éxito. Revisa los logs." >&2
  exit 1
fi
echo "Listo. Pólizas paramétricas sembradas para $CLIENTE_EMAIL."

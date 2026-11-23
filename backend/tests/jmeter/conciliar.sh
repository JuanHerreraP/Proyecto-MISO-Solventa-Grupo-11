#!/usr/bin/env bash
# Concilia la telemetría tras una prueba de carga: cuenta en SQS (cola + DLQ) y en la BD
# (siniestros con registrado_por=TELEMETRIA), y verifica la identidad de no-pérdida:
#   aceptados == procesados_bd + en_cola + en_vuelo + en_dlq
#
# Corre un script Python INLINE como tarea ECS (misma red/credenciales que el backend),
# porque reconciliar_telemetria.py no está en la imagen desplegada.
#
# Uso:
#   ACEPTADOS=12345 bash backend/tests/jmeter/conciliar.sh
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
STACK="${STACK:-solventa-mvp}"
ACEPTADOS="${ACEPTADOS:-}"

cd "$(git rev-parse --show-toplevel)"

CLUSTER=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Cluster'].OutputValue" --output text)
SERVICE=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Service'].OutputValue" --output text)
QUEUE_URL=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='QueueUrl'].OutputValue" --output text)
DLQ_URL=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='DlqUrl'].OutputValue" --output text)
LOG_GROUP=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='LogGroup'].OutputValue" --output text)
TASKDEF=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query "services[0].taskDefinition" --output text)
read -r SUBNETS SGS <<<"$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query "services[0].networkConfiguration.awsvpcConfiguration.[join(',',subnets),join(',',securityGroups)]" \
  --output text)"

PYCODE='
import os
from urllib.parse import quote
if os.environ.get("DB_HOST") and not os.environ.get("DATABASE_URL"):
    _h=os.environ.get("DB_HOST"); _u=quote(os.environ.get("DB_USER","solventa"),safe=""); _p=quote(os.environ.get("DB_PASSWORD",""),safe="")
    os.environ["DATABASE_URL"]=f"postgresql+psycopg://{_u}:{_p}@{_h}:5432/solventa?sslmode=require"
import boto3
from sqlalchemy import select, func
from app.infraestructura.database import SessionLocal, esperar_base_disponible
from app.siniestros.modelos_db import SiniestroDB
esperar_base_disponible()
sqs=boto3.client("sqs", region_name=os.environ.get("AWS_DEFAULT_REGION"))
def attr(url,name):
    r=sqs.get_queue_attributes(QueueUrl=url, AttributeNames=[name])
    return int(r["Attributes"][name])
en_cola=attr(os.environ["SQS_QUEUE_URL"],"ApproximateNumberOfMessages")
en_vuelo=attr(os.environ["SQS_QUEUE_URL"],"ApproximateNumberOfMessagesNotVisible")
en_dlq=attr(os.environ["SQS_DLQ_URL"],"ApproximateNumberOfMessages")
db=SessionLocal()
try:
    proc=db.scalar(select(func.count()).select_from(SiniestroDB).where(SiniestroDB.registrado_por=="TELEMETRIA"))
finally:
    db.close()
print(f"CONCIL procesados_bd={proc} en_cola={en_cola} en_vuelo={en_vuelo} en_dlq={en_dlq}")
total=proc+en_cola+en_vuelo+en_dlq
print(f"CONCIL total_observado={total}")
aceptados=os.environ.get("ACEPTADOS")
if aceptados:
    a=int(aceptados)
    print(f"CONCIL aceptados={a} cuadra={a==total} (nota: procesados_bd cuenta siniestros creados; SIN_COBERTURA no crea fila, ver doc)")
'

ENV_JSON="[{\"name\":\"SQS_QUEUE_URL\",\"value\":\"$QUEUE_URL\"},{\"name\":\"SQS_DLQ_URL\",\"value\":\"$DLQ_URL\"}"
[ -n "$ACEPTADOS" ] && ENV_JSON="$ENV_JSON,{\"name\":\"ACEPTADOS\",\"value\":\"$ACEPTADOS\"}"
ENV_JSON="$ENV_JSON]"

OVERRIDES=$(python3 - "$PYCODE" "$ENV_JSON" <<'JSON'
import json, sys
pycode, env = sys.argv[1], json.loads(sys.argv[2])
print(json.dumps({"containerOverrides":[{"name":"backend","command":["python","-c",pycode],"environment":env}]}))
JSON
)

NET="awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${SGS}],assignPublicIp=DISABLED}"
echo ">> Lanzando tarea de conciliación ..."
TASK_ARN=$(aws ecs run-task --cluster "$CLUSTER" --task-definition "$TASKDEF" \
  --launch-type FARGATE --platform-version 1.4.0 --network-configuration "$NET" \
  --overrides "$OVERRIDES" --query "tasks[0].taskArn" --output text)
aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK_ARN"
sleep 3
echo ">> Resultado:"
aws logs tail "$LOG_GROUP" --since 3m --format short 2>&1 | grep "CONCIL" | tail -10

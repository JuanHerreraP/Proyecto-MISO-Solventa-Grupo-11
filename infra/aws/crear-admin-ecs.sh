#!/usr/bin/env bash
# Lanza una tarea ECS puntual que ejecuta crear_admin.py en la red privada,
# con las mismas subredes, security group, cluster y rol que el servicio backend.
# Reutiliza la task definition del servicio y solo sobreescribe el comando y las
# variables de entorno del contenedor "backend".
#
# Uso:
#   AWS_REGION=us-east-1 \
#   STACK=solventa-mvp \
#   IMAGE="$BACKEND_REPO:$IMAGE_TAG" \
#   ADMIN_EMAIL=manager@solventa.local \
#   ADMIN_PASSWORD=password \
#   ADMIN_ROL=SERVICIO_INTERNO \
#   ./infra/aws/crear-admin-ecs.sh
#
# IMAGE es opcional: si se omite, usa la imagen de la task definition vigente.
# Requiere que la nueva imagen (con crear_admin.py) ya esté publicada en ECR.
set -euo pipefail

: "${AWS_REGION:?Define AWS_REGION}"
: "${STACK:=solventa-mvp}"
: "${ADMIN_EMAIL:?Define ADMIN_EMAIL}"
: "${ADMIN_PASSWORD:?Define ADMIN_PASSWORD}"
ADMIN_ROL="${ADMIN_ROL:-SERVICIO_INTERNO}"
export AWS_DEFAULT_REGION="$AWS_REGION"

echo "Descubriendo recursos del stack $STACK ..."
CLUSTER=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Cluster'].OutputValue" --output text)
SERVICE=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Service'].OutputValue" --output text)

# Task definition y configuración de red del servicio en ejecución.
TASKDEF=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query "services[0].taskDefinition" --output text)
read -r SUBNETS SGS <<<"$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query "services[0].networkConfiguration.awsvpcConfiguration.[join(',',subnets),join(',',securityGroups)]" \
  --output text)"

echo "Cluster:  $CLUSTER"
echo "TaskDef:  $TASKDEF"
echo "Subnets:  $SUBNETS"
echo "SG:       $SGS"

# Override del contenedor backend: ejecuta el script en vez de uvicorn.
# No se incluye ADMIN_PASSWORD en logs; va solo en el override de environment.
OVERRIDES=$(cat <<JSON
{
  "containerOverrides": [
    {
      "name": "backend",
      "command": ["python", "crear_admin.py"],
      "environment": [
        {"name": "ADMIN_EMAIL", "value": "${ADMIN_EMAIL}"},
        {"name": "ADMIN_PASSWORD", "value": "${ADMIN_PASSWORD}"},
        {"name": "ADMIN_ROL", "value": "${ADMIN_ROL}"}
      ]
    }
  ]
}
JSON
)

NET="awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${SGS}],assignPublicIp=DISABLED}"

echo "Lanzando tarea de bootstrap ..."
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

echo "Exit code del contenedor backend: $EXIT"
echo "Motivo de parada: $REASON"
echo "Revisa el detalle en el log group del stack (prefijo de stream: backend)."
if [ "$EXIT" != "0" ]; then
  echo "La tarea no terminó con éxito. Revisa los logs." >&2
  exit 1
fi
echo "Listo. El administrador quedó creado/actualizado."

#!/usr/bin/env bash
# Despliegue del stack solventa-mvp: construye y sube la imagen del backend
# (que incluye el worker SQS) y despliega el stack con esa etiqueta nueva.
#
# Autocontenido: descubre el repo ECR y los ARN de los secretos solo. No hay
# que editar nada a mano ni depender de parameters.json.
#
# Uso:
#   bash infra/aws/desplegar-mvp.sh                  # construye imagen + despliega
#   SALTAR_BUILD=true bash infra/aws/desplegar-mvp.sh  # solo redespliega (reusa la imagen vigente)
#
# Variables opcionales (tienen default, no hace falta tocarlas):
#   WORKER_CONCURRENCIA   concurrencia del worker (default: la del stack, 4)
#   WORKER_DESIRED_COUNT  tareas del worker (default: la del stack, 1)
#   EC_ORDENAR_DESEMBOLSO no aplica aquí (el worker lo lleva en false por el stack)
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
STACK="${STACK:-solventa-mvp}"
ECR_STACK="${ECR_STACK:-solventa-ecr}"

cd "$(git rev-parse --show-toplevel)"

echo ">> Comprobando sesión de AWS ..."
aws sts get-caller-identity >/dev/null

echo ">> Descubriendo el repositorio ECR del backend ..."
BACKEND_REPO=$(aws cloudformation describe-stacks --stack-name "$ECR_STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='BackendUri'].OutputValue" --output text)
REGISTRY="${BACKEND_REPO%%/*}"
echo "   Repo ECR: $BACKEND_REPO"

if [ -n "${BACKEND_IMAGE:-}" ]; then
  echo ">> Usando la imagen indicada en BACKEND_IMAGE (sin reconstruir): $BACKEND_IMAGE"
elif [ "${USAR_ULTIMA_IMAGEN:-false}" = "true" ]; then
  echo ">> USAR_ULTIMA_IMAGEN=true: tomando la imagen más reciente del repositorio ECR ..."
  ULTIMA_TAG=$(aws ecr describe-images --repository-name "${BACKEND_REPO##*/}" \
    --query "sort_by(imageDetails,& imagePushedAt)[-1].imageTags[0]" --output text)
  if [ -z "$ULTIMA_TAG" ] || [ "$ULTIMA_TAG" = "None" ]; then
    echo "ERROR: no encontré ninguna imagen en el repositorio ECR." >&2
    exit 1
  fi
  BACKEND_IMAGE="$BACKEND_REPO:$ULTIMA_TAG"
  echo "   Imagen: $BACKEND_IMAGE"
elif [ "${SALTAR_BUILD:-false}" = "true" ]; then
  echo ">> SALTAR_BUILD=true: se reutiliza la imagen vigente en la task definition del stack."
  BACKEND_IMAGE=$(aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Parameters[?ParameterKey=='BackendImage'].ParameterValue" --output text)
  if [ -z "$BACKEND_IMAGE" ] || [ "$BACKEND_IMAGE" = "None" ]; then
    echo "ERROR: no hay BackendImage previo en el stack; corre sin SALTAR_BUILD." >&2
    exit 1
  fi
else
  echo ">> Autenticando Docker contra ECR ..."
  aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"

  IMAGE_TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
  BACKEND_IMAGE="$BACKEND_REPO:$IMAGE_TAG"
  echo ">> Construyendo la imagen $BACKEND_IMAGE (incluye el worker SQS) ..."
  docker build -t "$BACKEND_IMAGE" backend
  echo ">> Subiendo la imagen a ECR ..."
  docker push "$BACKEND_IMAGE"
fi

echo ">> Descubriendo los ARN de los secretos ..."
JWT_SECRET_ARN=$(aws secretsmanager describe-secret --secret-id solventa-mvp-jwt \
  --query ARN --output text)
APP_SECRETS_ARN=$(aws secretsmanager describe-secret --secret-id solventa-mvp-app \
  --query ARN --output text)
# La versión de Postgres se toma SIEMPRE de la base YA EXISTENTE para no intentar un cambio de
# versión (RDS no permite downgrades). Se ignora deliberadamente cualquier POSTGRES_ENGINE_VERSION
# exportada en la terminal, que fue la causa de intentos previos de downgrade 16.11 -> 16.9.
POSTGRES_ENGINE_VERSION=""
DBID=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Database'].OutputValue" --output text 2>/dev/null || true)
if [ -n "${DBID:-}" ] && [ "$DBID" != "None" ]; then
  POSTGRES_ENGINE_VERSION=$(aws rds describe-db-instances --db-instance-identifier "$DBID" \
    --query "DBInstances[0].EngineVersion" --output text 2>/dev/null || true)
fi
POSTGRES_ENGINE_VERSION="${POSTGRES_ENGINE_VERSION:-16.11}"
echo ">> Versión de Postgres a usar (leída de la base actual, se ignora cualquier export): $POSTGRES_ENGINE_VERSION"

# La plantilla supera los 51.200 bytes (límite de CloudFormation para plantillas en línea),
# así que hay que subirla a un bucket S3. Se reutiliza el WebBucket del stack bajo un prefijo
# propio para no mezclar con el contenido de la web.
echo ">> Descubriendo bucket S3 para la plantilla ..."
TEMPLATE_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='WebBucket'].OutputValue" --output text 2>/dev/null || true)
if [ -z "${TEMPLATE_BUCKET:-}" ] || [ "$TEMPLATE_BUCKET" = "None" ]; then
  echo "ERROR: no encontré un bucket S3 para subir la plantilla (WebBucket)." >&2
  echo "       Define TEMPLATE_BUCKET=<mi-bucket> y reintenta." >&2
  exit 1
fi
echo "   Bucket plantilla: s3://$TEMPLATE_BUCKET/cfn-templates/"

# Parámetros opcionales del worker: solo se pasan si el usuario los define, para
# no sobreescribir el default del stack sin querer.
EXTRA_PARAMS=()
[ -n "${WORKER_CONCURRENCIA:-}" ] && EXTRA_PARAMS+=("WorkerConcurrencia=$WORKER_CONCURRENCIA")
[ -n "${WORKER_DESIRED_COUNT:-}" ] && EXTRA_PARAMS+=("WorkerDesiredCount=$WORKER_DESIRED_COUNT")

echo
echo ">> Parametros del despliegue:"
echo "   BackendImage         = $BACKEND_IMAGE"
echo "   JwtSecretArn         = $JWT_SECRET_ARN"
echo "   AppSecretsArn        = $APP_SECRETS_ARN"
echo "   Postgres             = $POSTGRES_ENGINE_VERSION"
[ ${#EXTRA_PARAMS[@]} -gt 0 ] && echo "   Extra                = ${EXTRA_PARAMS[*]}"
echo

echo ">> Desplegando el stack (tarda varios minutos; NO interrumpir) ..."
aws cloudformation deploy --stack-name "$STACK" \
  --template-file infra/aws/stack.json \
  --s3-bucket "$TEMPLATE_BUCKET" \
  --s3-prefix cfn-templates \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    BackendImage="$BACKEND_IMAGE" \
    JwtSecretArn="$JWT_SECRET_ARN" \
    AppSecretsArn="$APP_SECRETS_ARN" \
    PostgresEngineVersion="$POSTGRES_ENGINE_VERSION" \
    "${EXTRA_PARAMS[@]}"

echo
echo ">> Salidas del stack:"
aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs" --output table

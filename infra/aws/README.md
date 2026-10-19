# Publicar el MVP del Sprint 1 en AWS - Guía de despliegue paso a paso (replicable)

Receta lineal para desplegar el MVP de Solventa en AWS desde cero. La
plantilla (`stack.json`) ya está lista; esta guía es solo la secuencia de
comandos a ejecutar.

> Ejecutar todos los comandos **desde la raíz del repositorio**.
> **No copiar/pegar desde visores con resaltado de sintaxis**: a veces se cuelan
> fragmentos de HTML (`class="token..."`) que rompen los comandos. Teclear a mano
> o pegar en un editor de texto plano primero.

## Antes de empezar

Necesitas:

- **AWS CLI v2** autenticada (`aws sts get-caller-identity` debe responder) con
  permisos de CloudFormation, IAM, ECR, ECS, EC2/VPC/NAT, RDS, Secrets Manager,
  CloudWatch Logs, API Gateway, S3 y CloudFront.
- **Docker** (sirve el clásico; no hace falta `buildx`).
- **Node 20+** y **npm** para compilar la web.
- **Python 3** y **OpenSSL** para generar las llaves.
- **Git** (se usa el hash del commit para etiquetar la imagen).

> Esto crea recursos **facturables** (2 NAT Gateway, RDS `db.t3.micro`, ALB,
> Fargate), no capa gratuita. Al terminar la demo, retirar el stack (ver el
> final de esta guía).

Fija la región una vez por terminal:

```bash
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
aws sts get-caller-identity
```

## Paso 1 — Crear el repositorio ECR y subir la imagen de la API

```bash
# 1.1 Crear el repositorio de imágenes (idempotente).
aws cloudformation deploy --stack-name solventa-ecr \
  --template-file infra/aws/ecr.json

# 1.2 Guardar la URI del repositorio y autenticar Docker contra ECR.
export BACKEND_REPO=$(aws cloudformation describe-stacks --stack-name solventa-ecr \
  --query "Stacks[0].Outputs[?OutputKey=='BackendUri'].OutputValue" --output text)
export REGISTRY="${BACKEND_REPO%%/*}"
aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"

# 1.3 Construir y subir la imagen con una etiqueta única.
export IMAGE_TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
docker build -t "$BACKEND_REPO:$IMAGE_TAG" backend
docker push "$BACKEND_REPO:$IMAGE_TAG"
```

> Si tienes `buildx`, puedes usar `docker buildx build --platform linux/amd64
> --push -t "$BACKEND_REPO:$IMAGE_TAG" backend` en un solo paso. El `build`
> clásico de arriba funciona siempre que tu máquina sea x86_64, igual que Fargate.

## Paso 2 — Generar las llaves JWT y guardarlas en Secrets Manager

```bash
mkdir -p infra/secrets
chmod 700 infra/secrets
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out infra/secrets/private_key.pem
openssl pkey -in infra/secrets/private_key.pem -pubout \
  -out infra/secrets/public_key.pem
chmod 600 infra/secrets/*.pem

python3 - <<'PY'
import json
from pathlib import Path
p = Path('infra/secrets')
(p / 'jwt.json').write_text(json.dumps({
    'private_key': (p / 'private_key.pem').read_text(),
    'public_key': (p / 'public_key.pem').read_text(),
}))
(p / 'jwt.json').chmod(0o600)
PY

export JWT_SECRET_ARN=$(aws secretsmanager create-secret --name solventa-mvp-jwt \
  --secret-string file://infra/secrets/jwt.json --query ARN --output text)
echo "$JWT_SECRET_ARN"
```

> Estas llaves son solo para AWS; no subir `infra/secrets/` al repo. Si el
> secreto ya existe de un despliegue previo, reutilizar su ARN con
> `aws secretsmanager describe-secret --secret-id solventa-mvp-jwt`.

## Paso 3 — Elegir la versión de PostgreSQL y crear la infraestructura

```bash
# 3.1 Ver versiones de PostgreSQL disponibles para db.t3.micro en la región.
aws rds describe-orderable-db-instance-options --engine postgres \
  --db-instance-class db.t3.micro \
  --query 'OrderableDBInstanceOptions[].EngineVersion' --output text

# 3.2 Fijar una versión de esa lista (ej. 16.9).
export POSTGRES_ENGINE_VERSION=16.9

# 3.3 Generar el archivo de parámetros con los tres valores.
python3 - <<'PY'
import json, os
from pathlib import Path
values = {
    'BackendImage': os.environ['BACKEND_REPO'] + ':' + os.environ['IMAGE_TAG'],
    'JwtSecretArn': os.environ['JWT_SECRET_ARN'],
    'PostgresEngineVersion': os.environ['POSTGRES_ENGINE_VERSION'],
}
p = Path('infra/secrets/parameters.json')
p.write_text(json.dumps([{'ParameterKey': k, 'ParameterValue': v} for k, v in values.items()]))
p.chmod(0o600)
print(p.read_text())
PY

# 3.4 Validar y desplegar. Tarda varios minutos (VPC, NAT, RDS, ECS).
aws cloudformation validate-template --template-body "$(cat infra/aws/stack.json)"
aws cloudformation deploy --stack-name solventa-mvp \
  --template-file infra/aws/stack.json \
  --parameter-overrides file://infra/secrets/parameters.json \
  --capabilities CAPABILITY_IAM

# 3.5 Ver las salidas (URL pública, bucket web, cluster, etc.).
aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query "Stacks[0].Outputs" --output table
```

> Si falla con `ECS Deployment Circuit Breaker was triggered`, suele ser que el
> contenedor no quedó sano. Revisar los logs (prefijo de stream `backend`) con:
> `aws logs describe-log-groups --query "logGroups[?contains(logGroupName,'solventa')].logGroupName" --output text`
> y luego `aws logs tail <log-group> --since 15m --format short`.
> Si el stack queda en `ROLLBACK_COMPLETE`, hay que borrarlo antes de reintentar:
> `aws cloudformation delete-stack --stack-name solventa-mvp` y
> `aws cloudformation wait stack-delete-complete --stack-name solventa-mvp`.

## Paso 4 — Compilar y publicar la web

```bash
export WEB_BUCKET=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query "Stacks[0].Outputs[?OutputKey=='WebBucket'].OutputValue" --output text)

cd web && npm ci && VITE_API_URL="" npm run build && cd ..
aws s3 sync web/dist/ "s3://$WEB_BUCKET/" --cache-control no-cache
```

> `VITE_API_URL=""` deja rutas relativas para que las cookies queden en el mismo
> origen de CloudFront. Antes de este paso la web no carga aunque la API ya responda.

## Paso 5 — Verificar

```bash
export MVP_URL=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query "Stacks[0].Outputs[?OutputKey=='Url'].OutputValue" --output text)
echo "$MVP_URL"
curl --fail "$MVP_URL/salud"
curl --fail "$MVP_URL/openapi.json" -o /dev/null -w "%{http_code}\n"
```

En el navegador, abrir `$MVP_URL` y comprobar:

- Carga la página de inicio, registro, login y logout.
- Recarga directa de una ruta interna (p. ej. `/login`) no da 404.
- `/api/v1/ruta-inexistente` devuelve JSON de la API, no el HTML de React.

## Paso 6 — Crear el primer usuario administrador

El registro público solo crea usuarios `CLIENTE`. Para el primer administrador
se usa un script de un solo uso que corre como tarea ECS en la red privada.
La imagen desplegada ya incluye `crear_admin.py` (si vienes de una imagen vieja,
repetir pasos 1.3 y 3.3–3.4 con una etiqueta nueva antes de continuar).

```bash
chmod +x infra/aws/crear-admin-ecs.sh
AWS_REGION=us-east-1 \
STACK=solventa-mvp \
ADMIN_EMAIL=manager@solventa.local \
ADMIN_PASSWORD='una-contraseña-fuerte' \
ADMIN_ROL=SERVICIO_INTERNO \
./infra/aws/crear-admin-ecs.sh
```

El script descubre red/cluster/task definition solo, lanza la tarea y espera a
que termine; `Exit code: 0` significa que el admin quedó creado o actualizado
(es idempotente). Roles válidos en `backend/app/identidad/modelos.py`:
`SERVICIO_INTERNO` administra usuarios y socios; `INGENIERO_INTEGRACIONES`
administra socios de distribución.


## Actualizar un despliegue existente

- **API**: repetir el paso 1.3 con una etiqueta nueva, regenerar `parameters.json`
  (paso 3.3) y volver a desplegar (paso 3.4). Se reutiliza el mismo ARN de JWT.
- **Web**: repetir el paso 4. Con la caché desactivada no hace falta invalidar
  CloudFront.

## Retirar el ambiente (importante para no seguir facturando)

```bash
# La base tiene DeletionPolicy=Delete: respaldar antes lo que se quiera conservar.
aws cloudformation delete-stack --stack-name solventa-mvp
aws cloudformation wait stack-delete-complete --stack-name solventa-mvp
```

> Eliminar `solventa-mvp` borra la base y los NAT Gateway. **Se conservan** (por
> política de retención) el bucket web versionado, el repositorio ECR y el
> secreto JWT; retirarlos aparte si ya no se necesitan.

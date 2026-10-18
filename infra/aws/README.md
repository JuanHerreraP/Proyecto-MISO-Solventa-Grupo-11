# Publicar el MVP del Sprint 1 en AWS

## Arquitectura revisada contra la wiki

```text
Web / Android / socios → HTTPS CloudFront
                            ├─ SPA y activos → S3 privado (OAC)
                            └─ /api/* y documentación → HTTPS API Gateway HTTP API
                                                        → VPC Link
                                                        → HTTP ALB interno
                                                        → FastAPI en ECS Fargate privado
                                                            ├─ TLS → Aurora PostgreSQL
                                                            │        writer + reader en dos AZ
                                                            └─ KYC A/B/C simulados (sidecars)
```

La [revisión de coherencia](coherencia-arquitectura.md) compara esta plantilla,
el código y las decisiones de la wiki. Es una implementación parcial del diseño
objetivo para las seis HU del Sprint 1; no demuestra aún sus ASR de rendimiento,
conmutación o disponibilidad. No crea los servicios futuros de cotización,
suscripción, emisión, pagos o siniestros.

CloudFront entrega `https://<id>.cloudfront.net`, sin dominio propio. Web y API
comparten origen para cookies Secure y CSRF. Las peticiones de API viajan por
HTTPS hasta API Gateway; su integración al ALB usa HTTP **dentro de la VPC**,
como la vista de despliegue. El ALB no es público. El cifrado también en ese
tramo privado requeriría un listener TLS y certificado de origen.

API Gateway aplica límites de consumo y registra solicitudes. **La validación
JWT, roles y scopes sigue en FastAPI**; no hay authorizer en el gateway. No se
configura un authorizer JWT genérico porque la aplicación emite tokens propios
y tiene registro/login públicos, cookies web y OAuth de socios. La delegación
centralizada de autorización requiere un diseño posterior.

CloudFront no guarda caché de respuestas ni errores. Reenvía autorización,
cookies y query strings de la API. Una función reescribe las rutas de la SPA
al `index.html` solo en el comportamiento de S3; un error de API conserva su
código y cuerpo. S3 tiene acceso público bloqueado, cifrado, versionamiento y
solo concede lectura a esta distribución mediante OAC.

La VPC tiene dos subredes públicas para NAT, dos privadas de aplicación y dos
aisladas de datos. Cada zona tiene su NAT Gateway. ECS no tiene IP pública;
solo el ALB puede acceder a la API y solo las tareas acceden a Aurora en 5432.
Aurora Serverless v2 usa dos instancias en zonas distintas, 0,5–2 ACU por
instancia. El backend usa el endpoint writer del clúster, que sigue al escritor
después de un failover. Hay que medir la recuperación: dos AZ no prueban EC11.

El backend actual sigue siendo una API modular y una sola tarea/proceso:
consentimientos, perfiles y caché **se pierden al reiniciar o desplegar**;
usuarios, sesiones y socios persisten en PostgreSQL. Los despliegues detienen
la tarea anterior antes de iniciar la nueva y tienen una interrupción breve.
No habilitar réplicas, workers adicionales ni autoescalado hasta sacar el
estado compartido de memoria. Los sidecars KYC son dobles de prueba, no
servicios de negocio ni adaptadores Lambda reales.

## Requisitos

- AWS CLI v2 autenticada y una región con dos zonas y Aurora Serverless v2.
- Permisos para CloudFormation, IAM (crear/pasar roles), ECR, ECS, EC2/VPC/NAT,
  RDS/Aurora, Secrets Manager, CloudWatch Logs, API Gateway, S3 y CloudFront.
  Confirmar las restricciones si la cuenta es de laboratorio.
- Docker con Buildx, Python 3 y OpenSSL.

Se facturan, entre otros, **dos NAT Gateway, dos instancias Aurora Serverless
v2, ALB y Fargate**, incluso con poco tráfico. No se presupone capa gratuita.
No se han creado recursos automáticamente. Ejecutar desde la raíz:

```bash
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION="$AWS_REGION"
aws sts get-caller-identity
aws rds describe-orderable-db-instance-options --engine aurora-postgresql \
  --db-instance-class db.serverless \
  --query 'OrderableDBInstanceOptions[].EngineVersion' --output text
```

Elegir una versión de Aurora de esa lista antes de crear el stack:

```bash
read -r -p 'Versión Aurora validada en la región: ' AURORA_ENGINE_VERSION
export AURORA_ENGINE_VERSION
```

## 1. Crear el repositorio de la API y subir su imagen

```bash
aws cloudformation deploy --stack-name solventa-ecr \
  --template-file infra/aws/ecr.json
export BACKEND_REPO=$(aws cloudformation describe-stacks --stack-name solventa-ecr \
  --query 'Stacks[0].Outputs[?OutputKey==`BackendUri`].OutputValue' --output text)
export REGISTRY="${BACKEND_REPO%%/*}"
aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"
export IMAGE_TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
docker buildx build --platform linux/amd64 --push \
  -t "$BACKEND_REPO:$IMAGE_TAG" backend
```

ECR usa etiquetas inmutables; elegir una nueva en cada actualización. La misma
imagen ejecuta la API o cada simulador con comandos diferentes. La plataforma
coincide con la tarea Fargate x86_64. La web se publicará en S3, no en ECS.

## 2. Crear llaves exclusivas para AWS

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
```

No usar las llaves de desarrollo ni subir estos archivos. En actualizaciones,
reutilizar el ARN (`aws secretsmanager describe-secret --secret-id solventa-mvp-jwt`).
ECS inyecta los secretos y el backend materializa PEM en archivos temporales
privados. Aurora recibe una contraseña generada por Secrets Manager. Rotar
secretos exige reiniciar tareas y coordinar la contraseña de la base.

## 3. Validar y crear infraestructura

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
values = {
    'BackendImage': os.environ['BACKEND_REPO'] + ':' + os.environ['IMAGE_TAG'],
    'JwtSecretArn': os.environ['JWT_SECRET_ARN'],
    'AuroraEngineVersion': os.environ['AURORA_ENGINE_VERSION'],
}
p = Path('infra/secrets/parameters.json')
p.write_text(json.dumps([{'ParameterKey': k, 'ParameterValue': v} for k, v in values.items()]))
p.chmod(0o600)
PY
aws cloudformation validate-template --template-body file://infra/aws/stack.json
aws cloudformation deploy --stack-name solventa-mvp \
  --template-file infra/aws/stack.json \
  --parameter-overrides file://infra/secrets/parameters.json \
  --capabilities CAPABILITY_IAM
aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query 'Stacks[0].Outputs' --output table
```

La creación toma varios minutos. Si falla, revisar eventos de CloudFormation,
logs de ECS y logs de acceso de API Gateway. ECS tiene rollback ante fallos de
arranque. FastAPI prepara el esquema al iniciar. La base empieza vacía: este
procedimiento no migra el SQLite local.

## 4. Construir y publicar la web

```bash
export WEB_BUCKET=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query 'Stacks[0].Outputs[?OutputKey==`WebBucket`].OutputValue' --output text)
export WEB_DIST=$(mktemp -d /tmp/solventa-web.XXXXXX)
docker buildx build --target static --build-arg VITE_API_URL= \
  --output "type=local,dest=$WEB_DIST" web
aws s3 sync "$WEB_DIST/" "s3://$WEB_BUCKET/" --cache-control no-cache
```

`VITE_API_URL` vacío conserva las rutas relativas: las cookies web quedan en
el mismo origen. Las variables Vite se fijan al construir y nunca llevan
secretos. El Dockerfile conserva Caddy como etapa final para el Compose auxiliar;
AWS solo usa la etapa de exportación `static`. Antes de esta carga S3 aún no
tiene `index.html`, por lo que la web no estará disponible aunque la API sí.

## 5. Verificar y conectar Android

```bash
export MVP_URL=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query 'Stacks[0].Outputs[?OutputKey==`Url`].OutputValue' --output text)
curl --fail "$MVP_URL/salud"
curl --fail "$MVP_URL/openapi.json"
curl --fail "$MVP_URL/login"
cd android
./gradlew assembleDebug -Psolventa.apiBaseUrl="$MVP_URL/"
```

Android ya soporta esa propiedad; necesita la **barra final** y no se despliega
como servidor. Compartir el APK para la demo.

Verificar en el navegador registro, login, recarga directa de `/admin/socios/nuevo`
y logout. Confirmar que `/api/v1/ruta-inexistente` responde un error de API y
no el HTML de React. Probar registro/login Android, HU24 y HU10/HU11 con los
roles autorizados. KYC y Open Finance/Open Data siguen siendo simulados.
La URL `ApiUrl` permite diagnosticar API Gateway directamente; es otro acceso
al mismo gateway, no una vía al ALB. Su uso web requeriría configurar CORS;
para el MVP usar `Url` de CloudFront.

## Actualizar, respaldar y retirar

Para la API, publicar otra etiqueta, regenerar los parámetros y desplegar con
el mismo ARN y versión Aurora. Para la web, repetir el paso 4. Con caché
desactivado no hace falta invalidación. Conservar imágenes y versiones de S3
permite volver a una entrega anterior; las migraciones de datos requieren su
propio plan. GitHub Actions sigue siendo CI: no se añadió CD automático.

Aurora tiene siete días de backups, cifrado, protección de borrado y snapshot
al eliminar/reemplazar el clúster. Esto no respalda el estado de la API en
memoria. Antes de retirar el ambiente, respaldar datos y desactivar
explícitamente la protección de borrado del clúster. Eliminar `solventa-mvp`
retira también los NAT Gateway; conserva el snapshot y el bucket web versionado.
Los repositorios ECR se conservan y el secreto JWT está fuera del stack.
Revisar y retirar conscientemente los recursos retenidos y sus costos.

Referencias AWS: [integración privada con ALB](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html),
[Aurora Serverless v2](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-rds-dbcluster-serverlessv2scalingconfiguration.html).

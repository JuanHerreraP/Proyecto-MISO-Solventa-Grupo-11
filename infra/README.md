# MVP en AWS: ECS Fargate + RDS

El despliegue requerido está en [aws/README.md](aws/README.md). Incluye imágenes
Docker para la API, ECR, ECS Fargate privado, RDS PostgreSQL (`db.t3.micro`),
API Gateway, Secrets Manager, CloudWatch, ALB interno y web estática en S3 +
CloudFront. Para replicarlo paso a paso, seguir la receta en
[aws/DESPLIEGUE.md](aws/DESPLIEGUE.md).

Los módulos de identidad, socios, enriquecimiento y perfilamiento viven hoy en
una sola API. Los tres proveedores KYC son simuladores separados. Open Finance
y Open Data siguen usando los simuladores en proceso existentes.

`compose.yaml` es una alternativa auxiliar para ejecutar los contenedores en
una máquina con Docker Compose v2; **no es el despliegue de ECS**. El archivo
`backend/docker-compose.yml` anterior sigue sirviendo para la base local.

## Compose auxiliar con dominio HTTPS

Desde esta carpeta, copiar `.env.example` a `.env`, definir `SITE_ADDRESS` y una
contraseña hexadecimal, y crear `secrets/private_key.pem` y
`secrets/public_key.pem`. La llave privada debe ser legible por UID 10001 del
contenedor (por ejemplo propietario 10001 y modo 0400). No usar las llaves de
desarrollo del repositorio. Apuntar el DNS al servidor y permitir 80/443.

```bash
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml up -d --build --wait
docker compose --env-file .env -f compose.yaml ps
```

Caddy obtiene el certificado y envía `/api/*`, `/salud` y `/docs` a la API;
el resto sirve la SPA. PostgreSQL y KYC no publican puertos al host. Los datos
y certificados usan volúmenes; `down -v` los elimina. Este Compose necesita un
dominio para obtener HTTPS automáticamente.

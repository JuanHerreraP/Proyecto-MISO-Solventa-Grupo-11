# Infraestructura

Definición del ambiente en AWS y del despliegue continuo. Pendiente.

Para el despliegue continuo del backend hacen falta: un repositorio en ECR, un servicio en ECS Fargate y un rol de AWS asumible desde GitHub Actions por OIDC. Con eso se agrega un workflow `deploy.yml` que construya la imagen de `backend/Dockerfile` y actualice el servicio al fusionar a `main`.

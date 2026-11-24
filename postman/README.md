# Colección de Postman

| Archivo | Contenido |
| --- | --- |
| `Solventa.postman_collection.json` | Flujo de la demo (22 requests con pruebas) y referencia de los 97 endpoints del OpenAPI |
| `Solventa-local.postman_environment.json` | Backend local (`http://localhost:8000`) |
| `Solventa-AWS.postman_environment.json` | MVP en AWS: reemplazar `baseUrl` por la salida `Url` del stack |
| `ejecutar-flujo.sh` | Ejecuta el flujo completo con Newman, leyendo el OTP del log del backend |

## Flujo de la demo

Cada request guarda en el ambiente lo que usa el siguiente (`token`, `cliente_id`, `cotizacion_id`,
`poliza_id`, `siniestro_id`…) y verifica la respuesta con pruebas.

1. **Cliente: registro, cotización y pago.** Salud del backend, registro con KYC simulado, inicio de
   sesión, perfil, cotización de un seguro de viaje, pago con tarjeta, comprobante, contrato y envío del
   OTP de firma.
2. **Firma, póliza y siniestro.** Firma con el OTP, billetera, certificado con QR, historial de la
   póliza, registro de un siniestro, lista de siniestros y notificaciones.
3. **Operaciones: aprobar el siniestro.** El usuario `SERVICIO_INTERNO` crea un usuario de
   Operaciones, que ve la bandeja y aprueba el siniestro con su desembolso.

La carpeta **Referencia: todos los endpoints** tiene los 97 endpoints agrupados por etiqueta del
OpenAPI, con el token de la colección.

## Usarla en Postman

1. Importar la colección y los dos ambientes (*Import → File*).
2. Elegir el ambiente y completar `admin_password` (y, en AWS, `baseUrl`).
3. Ejecutar la carpeta 1 (*Run folder*).
4. Copiar el OTP del log del backend en la variable `otp`:
   - Local: `[FIRMA SIMULADA] OTP 123456 ... (proceso FIR-...)` en la consola del backend.
   - AWS: `aws logs filter-log-events --log-group-name <grupo> --filter-pattern '"FIR-..."'`.
5. Ejecutar las carpetas 2 y 3.

## Ejecutarla con Newman

```bash
# Local (backend con uvicorn, log en un archivo)
uvicorn app.main:app 2>&1 | tee /tmp/backend.log
ADMIN_PASSWORD='Manager123!' BACKEND_LOG=/tmp/backend.log ./postman/ejecutar-flujo.sh local

# AWS (requiere AWS CLI autenticada)
LOG_GROUP=$(aws cloudformation describe-stack-resource --stack-name solventa-mvp --logical-resource-id Logs \
  --query StackResourceDetail.PhysicalResourceId --output text)
ADMIN_PASSWORD='...' LOG_GROUP="$LOG_GROUP" BASE_URL=https://<distribucion>.cloudfront.net \
  ./postman/ejecutar-flujo.sh aws
```

Resultado contra el backend local (22 requests, 34 aserciones, 0 fallas): [docs/evidencias/postman](../docs/evidencias/postman/README.md), con capturas y reportes HTML de Newman.
(22 requests, 34 pruebas, 0 fallas).

## Regenerar la referencia

La carpeta de referencia sale del OpenAPI de FastAPI (`/openapi.json`). Si cambian los endpoints,
importar de nuevo `http://localhost:8000/openapi.json` en Postman o regenerarla con
`openapi-to-postmanv2`.

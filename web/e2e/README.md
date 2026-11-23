# Pruebas E2E web

Los escenarios de Playwright viven en esta carpeta y consumen la API configurada mediante
`VITE_API_URL`. Por defecto, Playwright inicia Vite en `http://localhost:5173` para mantener
la sesión web y la API bajo el mismo host.

```bash
npm run test:e2e:install
VITE_API_URL=http://localhost:8000 npm run test:e2e
```

Las pruebas crean usuarios y datos aislados mediante la API. Para el escenario de asesor se
requiere un usuario `SERVICIO_INTERNO` capaz de crear el asesor de prueba:

```bash
E2E_ADMIN_EMAIL=admin@email.com \
E2E_ADMIN_PASSWORD='contraseña-local' \
VITE_API_URL=http://localhost:8000 \
npm run test:e2e
```

### OTP de la firma electrónica

El proveedor de firma simulado escribe el OTP en el log del backend
(`[FIRMA SIMULADA] OTP ... (proceso FIR-...)`). Las pruebas lo leen de la primera fuente
configurada, reintentando unos segundos mientras el log llega:

| Ambiente | Variable | Ejemplo |
| --- | --- | --- |
| AWS (ECS → CloudWatch) | `E2E_LOG_GROUP` | grupo de logs del backend; requiere AWS CLI autenticada |
| Backend con `uvicorn` | `E2E_BACKEND_LOG` | `uvicorn app.main:app 2>&1 \| tee /tmp/backend.log` y `E2E_BACKEND_LOG=/tmp/backend.log` |
| Docker Compose | `E2E_COMPOSE_FILE`, `E2E_COMPOSE_ENV`, `E2E_COMPOSE_SERVICE` | por defecto `infra/compose.yaml`, `.env` y `backend` |

Para obtener el grupo de logs del stack de AWS:

```bash
aws cloudformation describe-stack-resource --stack-name <stack> --logical-resource-id Logs \
  --query StackResourceDetail.PhysicalResourceId --output text
```

`E2E_OTP` fija un único código y solo sirve para ejecutar una prueba con una sola firma, porque
cada proceso de firma genera un OTP nuevo. Nunca use credenciales ni OTP de producción.
Playwright carga automáticamente las variables guardadas en `web/.env.e2e.local`.

En GitHub Actions, el flujo manual **E2E web (nube)** (`.github/workflows/e2e-cloud.yml`) ejecuta
estas pruebas contra el ambiente de AWS y publica el reporte como artefacto.

Cada ejecución conserva automáticamente las capturas y el reporte HTML dentro de una única
carpeta:

```bash
npm run test:e2e
npx playwright show-report e2e/evidencias/report
```

Los artefactos quedan en `web/e2e/evidencias/artifacts/` y el reporte en
`web/e2e/evidencias/report/`. La carpeta está ignorada por Git. No se generan trazas ni videos
porque pueden contener tokens, cookies o cuerpos de solicitudes.

Para probar un despliegue existente sin iniciar Vite:

```bash
E2E_BASE_URL=https://ejemplo.test npm run test:e2e
```

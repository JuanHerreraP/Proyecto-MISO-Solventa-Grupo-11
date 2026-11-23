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

En local, el código OTP se obtiene del log del proveedor simulado de Docker. En un ambiente de
pruebas externo puede suministrarse con `E2E_OTP`. Nunca use credenciales ni OTP de producción.
Playwright carga automáticamente las variables guardadas en `web/.env.e2e.local`.

Para conservar capturas y un reporte HTML versionable incluso cuando las pruebas pasan:

```bash
E2E_EVIDENCE=1 npm run test:e2e
npx playwright show-report e2e/evidence/report
```

Los artefactos quedan en `web/e2e/evidence/artifacts/` y el reporte en
`web/e2e/evidence/report/`. Estas carpetas se pueden subir al repositorio. Las trazas y videos
no se generan en este modo porque pueden contener tokens, cookies o cuerpos de solicitudes.

Para probar un despliegue existente sin iniciar Vite:

```bash
E2E_BASE_URL=https://ejemplo.test npm run test:e2e
```

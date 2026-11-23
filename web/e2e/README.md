# Pruebas E2E web

Los escenarios de Playwright viven en esta carpeta y consumen la API configurada mediante
`VITE_API_URL`. Por defecto, Playwright inicia Vite en `http://127.0.0.1:5173`.

```bash
npm run test:e2e:install
VITE_API_URL=http://localhost:8000 npm run test:e2e
```

Para probar un despliegue existente sin iniciar Vite:

```bash
E2E_BASE_URL=https://ejemplo.test npm run test:e2e
```

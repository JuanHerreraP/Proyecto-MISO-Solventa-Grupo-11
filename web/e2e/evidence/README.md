# Evidencias E2E

Ejecuta desde `web/`:

```bash
E2E_EVIDENCE=1 npm run test:e2e
```

Las capturas se guardan en `artifacts/` y el reporte navegable en `report/`. Ambos directorios
se versionan como evidencia de la ejecución. No se almacenan trazas ni videos para evitar subir
tokens, cookies o cuerpos de solicitudes al repositorio.

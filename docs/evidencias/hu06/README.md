# Evidencias de la HU06 (BPM-30): prestadores cercanos y asistencia en sitio

Guía de la prueba manual en la app Android (emulador) contra el backend local. Las capturas
(`01-*.png`, `02-*.png`, …) se agregan a esta carpeta durante la demo, en el orden del checklist.

## Preparación

1. Backend en `backend/`:
   ```bash
   source .venv/bin/activate
   CLIENTE_EMAIL=tu-correo python sembrar_polizas.py   # pólizas de viaje y dispositivos vigentes
   python sembrar_prestadores.py                        # prestadores demo (Bogotá y Mosquera)
   uvicorn app.main:app --reload
   ```
2. En el emulador, controles extendidos → **Location**, fija la ubicación en el **centro de
   Bogotá**: latitud `4.7110`, longitud `-74.0721`. Para los casos del occidente usa Mosquera
   `4.7059, -74.2302` o Madrid `4.7328, -74.2635`.
3. Compila la app con la clave de Maps:
   `./gradlew assembleDebug -Psolventa.mapsApiKey=MI_CLAVE` (sin clave, la lista funciona pero el
   mapa no carga mosaicos).

## Checklist

| # | Caso | Qué demuestra |
|---|---|---|
| 1 | Entrada desde el inicio | La acción **«Asistencia en sitio»** abre el flujo (solo con sesión). |
| 2 | Selección de póliza | Solo aparecen pólizas vigentes de `VIAJE` o `PROTECCION_DISPOSITIVOS`. |
| 3 | Selección de servicio | Para dispositivos: Diagnóstico técnico y Reparación de dispositivo. |
| 4 | Permiso de ubicación | La app pide el permiso; al concederlo busca prestadores. |
| 5 | Permiso denegado | Si se niega, la app no se cierra: avisa y ofrece **Reintentar**. |
| 6 | Mapa + lista | Se muestran los prestadores en el mapa y en una lista ordenada por distancia. |
| 7 | Filtrado | No aparecen el inactivo, el de servicio incompatible ni el de Medellín (fuera del radio). |
| 8 | Caso Mosquera | Con ubicación en Mosquera, aparecen los prestadores de Mosquera primero. |
| 9 | Sin prestadores | Fuera de cobertura, se ofrece **Reintentar** y **Ampliar a 50 km**. |
| 10 | Confirmación | Resumen de póliza, servicio, prestador, distancia y ubicación; observaciones opcionales. |
| 11 | Solicitud exitosa | Tras `201`, se muestra el id y el estado `SOLICITADA`. |
| 12 | Mis asistencias | La solicitud aparece en la lista del cliente. |
| 13 | Cancelación | La asistencia pasa a `CANCELADA`; el registro no se elimina y el botón desaparece. |
| 14 | Caso viaje | Con una póliza de viaje y **Atención médica**, aparece «Centro Médico Aliado». No se crea un siniestro. |
| 15 | Seguridad | Sin token, 401; con póliza o asistencia ajena, 403; el cliente_id nunca se envía. |
| 16 | Pruebas automatizadas | Backend (`pytest`) y Android (`testDebugUnitTest`) en verde; `lint` sin errores. |

## Flujo esperado — Protección de dispositivos

```text
Inicio → Asistencia en sitio → Protección de dispositivos → Reparación de dispositivo
→ Permitir ubicación → Mapa + lista (Solventa Tech Centro 0,5 km; TechCare Norte 1,8 km)
→ Seleccionar Solventa Tech Centro → Observaciones → Solicitar → ASI-… SOLICITADA
→ Mis asistencias → Cancelar → CANCELADA
```

## Flujo esperado — Viaje

```text
Inicio → Asistencia en sitio → Seguro de viaje → Atención médica → Ubicación
→ Prestadores cercanos → Centro Médico Aliado → Solicitar asistencia
```

No se crea un siniestro automáticamente.

## Verificación por API (opcional)

```bash
# Con un access token de CLIENTE:
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/prestadores/cercanos?poliza_id=POL-001&servicio=REPARACION_DISPOSITIVO&latitud=4.711&longitud=-74.072&radio_km=25"
```

La respuesta llega ordenada por `distancia_km` ascendente y con `Cache-Control: no-store`.

## Seguimiento operativo — rol Operaciones/Siniestros (HU06 ampliación)

El rol `OPERACIONES_SINIESTROS` consulta y da seguimiento desde Swagger; el cliente ve el estado
y el ETA en la app. Flujo de extremo a extremo:

1. **Cliente (app):** solicita asistencia → queda `SOLICITADA` (ASI-…).
2. **Operaciones (Swagger, token de un usuario `OPERACIONES_SINIESTROS`):**
   - `GET /api/v1/operaciones/asistencias` → ve la solicitud en la bandeja.
   - `GET /api/v1/operaciones/asistencias/{id}` → detalle con `cliente_id` y `numero_poliza`.
   - `POST /api/v1/operaciones/asistencias/{id}/aceptacion` con `{ "tiempo_estimado_llegada_minutos": 20 }`
     (o `{}` si el ETA aún no está disponible) → pasa a `ACEPTADA`, fija `aceptada_en`.
   - (opcional) `PATCH /api/v1/operaciones/asistencias/{id}/seguimiento` con
     `{ "tiempo_estimado_llegada_minutos": 15 }` → actualiza el ETA.
3. **Cliente (app):** en **Mis asistencias** recarga y ve:
   - `ACEPTADA` + "Tiempo estimado de llegada: 20 min", o
   - `ACEPTADA` + "Aún no disponible" si se aceptó con `{}`.

| # | Caso | Qué demuestra |
|---|---|---|
| S1 | Cliente no accede a `/operaciones/*` | Responde 403 (separación de permisos). |
| S2 | Operaciones lista y ve detalle | Bandeja y detalle con `cliente_id`/`numero_poliza`. |
| S3 | Aceptar con ETA | `estado = ACEPTADA`, `aceptada_en != null`, ETA = 20. |
| S4 | Aceptar sin ETA (`{}`) | `estado = ACEPTADA`, ETA = `null`. |
| S5 | Actualizar ETA (PATCH) | ETA pasa de `null` a 15. |
| S6 | Aceptar dos veces / aceptar cancelada | 409 (`ASISTENCIA_YA_ACEPTADA` / `ASISTENCIA_CANCELADA`). |
| S7 | PATCH sobre `SOLICITADA` | 409 `TRANSICION_ESTADO_INVALIDA`. |
| S8 | App muestra el seguimiento | "Aceptada" + "20 min" o "Aún no disponible"; nunca "0 min". |

No se crea un siniestro al aceptar o actualizar el ETA. No hay tracking GPS del prestador ni
cálculo automático de rutas: el ETA es un dato operativo.

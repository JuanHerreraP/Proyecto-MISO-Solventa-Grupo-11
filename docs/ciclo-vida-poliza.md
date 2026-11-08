# Ciclo de vida de la póliza: cancelación (HU22 / BPM-35)

Esta página cubre la **cancelación**. La renovación se documenta aparte cuando se implemente.

## Reglas

- La cancelación es **inmediata e irreversible**: la póliza pasa a `CANCELADA` el mismo día y deja de aparecer entre las coberturas activas. Su certificado se conserva como constancia.
- Pueden cancelar el **cliente titular** (sus pólizas; una ajena responde 404) y el **asesor de ventas** (solo las pólizas de sus ventas asistidas, es decir, de cotizaciones que él originó; otra póliza responde 403 `ACCESO_DENEGADO`). Cualquier otro rol recibe 403. La cancelación registra el rol y el id de quien la pidió.
- **No se puede cancelar** si la póliza no está vigente (`POLIZA_NO_VIGENTE`) ni mientras tenga un siniestro en trámite (`SINIESTRO_EN_TRAMITE`): registrado, en evaluación, o aprobado con la indemnización aún sin desembolsar por completo. Un siniestro rechazado no bloquea.
- Si la cancelación no se puede procesar, la póliza queda exactamente como estaba.

## Saldo a favor

Sin penalización, por periodo pagado:

```
saldo = prima × días sin usar ÷ días del periodo
```

- Los días sin usar son los que quedan **después de hoy** (hoy cuenta como usado), limitados al total del periodo; un periodo que aún no empieza se devuelve completo.
- Se redondea a centavos (`ROUND_HALF_UP`).
- Ejemplo: prima 150.000, vigencia 2026-01-01 a 2026-12-31 (365 días), cancelación el 2026-07-02 → 182 días sin usar → **74.794,52**.
- El sistema solo **registra** la devolución como `PENDIENTE` (o `SIN_SALDO` si es 0). No mueve dinero; gestionarla es otra historia.

## API

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/v1/polizas/{poliza_id}/cancelacion` | Condiciones: `cancelable`, `bloqueos`, `consecuencias`, `motivos`, saldo estimado y, si ya se canceló, `cancelacion`. No guarda nada. |
| POST | `/api/v1/polizas/{poliza_id}/cancelacion` | Cancela. Cuerpo: `{"motivo", "detalle"?, "confirmo": true}`. |

- `confirmo` debe ser `true`; si no, 422 `CONFIRMACION_REQUERIDA`.
- `Idempotency-Key` (opcional, máx. 100): repetir la misma solicitud devuelve la misma cancelación con 200; usar la clave con otro motivo/detalle responde 409 `CLAVE_IDEMPOTENCIA_REUTILIZADA`.
- 409 con `codigo` = primer bloqueo y la lista completa en `bloqueos`.
- Las respuestas llevan `Cache-Control: no-store` y no exponen huella, IP, user agent ni clave.

Motivos: `YA_NO_LA_NECESITO`, `PRECIO_ALTO`, `OTRA_ASEGURADORA`, `COBERTURA_INSUFICIENTE`, `OTRO`.

## Persistencia

Tabla nueva `cancelaciones` (se crea sola con `create_all`; no cambia `polizas`). Restricción única por póliza: una póliza se cancela una sola vez. La cancelación y el cambio de estado de la póliza se guardan en **una sola transacción**. Cada registro guarda quién, desde qué IP/user agent, el motivo y el cálculo del saldo.

## Código

- Dominio: `backend/app/polizas/dominio/cancelacion.py`
- Caso de uso: `backend/app/polizas/cancelacion.py`
- Repositorio: `backend/app/polizas/repositorio_cancelaciones.py`
- API: `backend/app/api/cancelaciones.py`
- Pruebas: `backend/tests/cancelaciones/`

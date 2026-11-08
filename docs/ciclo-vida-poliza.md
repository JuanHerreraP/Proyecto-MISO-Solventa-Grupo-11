# Ciclo de vida de la póliza: renovación y cancelación (HU22 / BPM-35)

Esta página cubre la **renovación** y la **cancelación** de pólizas (backend). La renovación va primero porque la cancelación depende de ella cuando se renueva con anticipación.

## Renovación

### Reglas

- Renuevan los ramos **vida**, **protección de dispositivos** y **paramétrico**. El seguro de viaje no se renueva (`RAMO_NO_RENOVABLE`).
- Se puede renovar desde **30 días antes del vencimiento** (`FUERA_DE_VENTANA` antes de eso). Una póliza vencida o cancelada no se renueva (`POLIZA_NO_VIGENTE`): hay que contratar una nueva.
- Una póliza ya renovada con anticipación no se renueva otra vez hasta que se acerque su nuevo vencimiento (`YA_RENOVADA`).
- **Continuidad:** la nueva vigencia empieza el día siguiente al fin de la actual y la póliza conserva su número. Dura los mismos meses contratados (`meses_cobertura`); si el riesgo no se define por meses, los mismos días. El periodo anterior queda guardado en la renovación.
- **Prima recalculada** con el rating y el perfil de riesgo vigentes, más la prima de las coberturas opcionales que el cliente agregó con endosos (`prima_nueva = prima_principal + prima_opcionales`). Si el perfil vigente es rechazado, no se renueva (`RIESGO_NO_ASEGURABLE`); si los datos del riesgo ya no son válidos o no existen, tampoco (`SIN_DATOS_DE_RIESGO`).
- Renuevan el **cliente titular** y el **asesor de la venta asistida** (misma regla de acceso que la cancelación); el pago lo hace siempre el cliente.

### Flujo

1. `GET /api/v1/polizas/{poliza_id}/renovacion` — propuesta: `renovable`, `bloqueos`, `renovable_desde`, `vigencia_actual`, `nueva_vigencia`, `coberturas` (con su prima), `prima_actual`, `prima_principal`, `prima_opcionales`, `prima_nueva`, `condiciones` y, si hay una en curso esperando el pago, `renovacion`. No guarda nada.
2. `POST /api/v1/polizas/{poliza_id}/renovacion` — el cliente confirma. Recalcula en el servidor y crea una **cotización de renovación** (vigente 7 días). Devuelve la renovación con `cotizacion_id` y `prima_total` (el monto). 201 si la crea; 200 si repite la solicitud (misma `Idempotency-Key` o ya había una vigente). 409 con `codigo` = primer bloqueo si no se puede renovar. La póliza **no cambia** todavía.
3. El cliente paga esa cotización con el recaudo de siempre: `POST /api/v1/pagos` (tarjeta o PSE).
4. Cuando el pago queda **APROBADO** (en la respuesta, o por la confirmación asíncrona de la pasarela en PSE), la póliza toma la nueva vigencia y la prima cobrada, en una sola transacción. La cotización pasa a `ACEPTADA`.
5. `GET /api/v1/polizas/{poliza_id}/renovacion/{renovacion_id}` — estado para saber si el pago ya renovó la póliza.

### Estados de la renovación

| Estado | Significa |
| --- | --- |
| `PENDIENTE_PAGO` | Creada, esperando el pago. Un pago rechazado la deja aquí: el cliente puede reintentar con otro medio. |
| `APLICADA` | Pago aprobado; la póliza ya tiene la nueva vigencia. |
| `VENCIDA` | La cotización venció sin pago (se deriva, no se guarda). La póliza no cambió; se puede iniciar otra renovación. |
| `NO_APLICADA` | Se pagó pero la póliza ya no se podía renovar (p. ej. se canceló antes). Queda con `motivo_no_aplicada` para gestionar la devolución. |

Si la renovación no se puede completar, la póliza queda **exactamente como estaba**.

### Garantías

- Aplicar es **idempotente**: el aviso del pago y la consulta del cliente pueden coincidir sin renovar dos veces.
- Si el aviso del pago falla, el pago no se deshace y la siguiente consulta de la renovación (o de la propuesta) aplica el pago aprobado pendiente.
- Una póliza se renueva una sola vez por periodo (restricción única `poliza_id` + `nuevo_inicio`); el identificador es `REN-{poliza_id}-{AAAAMMDD}`.
- La respuesta no expone clave de idempotencia, IP ni user agent.

### Renovar con anticipación

La póliza muestra el nuevo periodo apenas se aplica la renovación, aunque aún no empiece: mientras tanto sigue vigente por el periodo anterior (`fecha_inicio` futura). Los endosos se calculan sobre el nuevo periodo. Si se cancela en ese lapso, el saldo suma el periodo en curso (días sin usar) y el periodo nuevo completo.

### Persistencia

Tabla nueva `renovaciones` (se crea sola con `create_all`; no cambia `polizas`), con el periodo anterior y el nuevo, las primas, la cotización, el pago y la auditoría (quién, rol, IP, user agent).

### Límites conocidos

- El certificado PDF original no se regenera con la nueva vigencia (los documentos emitidos son inmutables); la póliza sí expone las fechas nuevas.
- Una renovación pagada pero no aplicable no devuelve el dinero: solo queda registrada.


# Cancelación

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

## Código de la cancelación

- Dominio: `backend/app/polizas/dominio/cancelacion.py`
- Caso de uso: `backend/app/polizas/cancelacion.py`
- Repositorio: `backend/app/polizas/repositorio_cancelaciones.py`
- API: `backend/app/api/cancelaciones.py`
- Pruebas: `backend/tests/cancelaciones/`

## Código de la renovación

- Dominio: `backend/app/polizas/dominio/renovacion.py`
- Caso de uso: `backend/app/polizas/renovacion.py` (acceso compartido en `backend/app/polizas/acceso.py`)
- Repositorio: `backend/app/polizas/repositorio_renovaciones.py`
- API: `backend/app/api/renovaciones.py`; el pago aprobado se enlaza en `backend/app/api/pagos.py` y `backend/app/pagos/servicio.py` (`al_aprobar`)
- Pruebas: `backend/tests/renovaciones/`

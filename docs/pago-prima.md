# Pago de primas pendientes (HU21)

Esta página cubre el **backend** de HU21: el listado de lo que el cliente debe pagar o firmar, el comprobante del pago y las garantías contra el doble cobro. El pago en sí reutiliza el recaudo de [HU13](recaudo-pagos.md). La parte de Android va aparte.

## Qué es una prima pendiente

El cliente consulta `GET /api/v1/primas-pendientes` y ve, en un solo listado, lo que debe resolver para tener su cobertura al día. Cada ítem tiene un `tipo` y una `accion`:

| `tipo` | Cuándo aparece | `accion` | Qué muestra |
| --- | --- | --- | --- |
| `RENOVACION` | Renovación iniciada y sin pagar ([HU22](ciclo-vida-poliza.md)) | `PAGAR` | Número de póliza, valor y fecha límite |
| `COTIZACION` | Cotización vigente sin pagar | `PAGAR` | Ramo y número de cotización, valor y fecha límite. **No hay número de póliza**: la póliza se emite al firmar el contrato |
| `FIRMA_PENDIENTE` | Cotización pagada cuyo contrato falta firmar, es decir, sin póliza emitida | `FIRMAR` | El valor ya pagado y el mensaje "Firma tu contrato en el portal web para emitir tu póliza." No hay nada que pagar ni fecha límite |

El tercer tipo es un aviso: hoy la firma solo existe en el portal web. Cuando la app pueda firmar, solo cambia lo que hace el cliente con ese ítem; el listado no cambia.

## Flujo

1. `GET /api/v1/primas-pendientes` — lista lo pendiente, las más urgentes primero.
2. El cliente elige un ítem de `accion = PAGAR` y confirma el monto (`monto`, `moneda`).
3. Paga con `POST /api/v1/pagos` sobre el `cotizacion_id` del ítem, con tarjeta o PSE, como en [HU13](recaudo-pagos.md).
4. Si el pago se **aprueba**: la renovación se aplica (si lo era), la prima sale del listado y se genera el comprobante.
5. `GET /api/v1/pagos/{pago_id}/comprobante` — el comprobante para mostrar en pantalla.
6. Si se **rechaza**: no cambia nada, la prima sigue pendiente y el cliente puede intentarlo de nuevo con otra `Idempotency-Key`.

## Endpoints

| Método y ruta | Quién | Devuelve |
| --- | --- | --- |
| `GET /api/v1/primas-pendientes` | Cliente | `{"primas": [...], "total": n}` |
| `GET /api/v1/pagos/{pago_id}/comprobante` | Cliente, solo sus pagos | El comprobante del pago aprobado |

Ambos responden `Cache-Control: no-store`. Un actor que no es el cliente recibe 403.

Además, el pago que devuelven `POST /api/v1/pagos`, `GET /api/v1/pagos` y `GET /api/v1/pagos/{pago_id}` incluye el campo **`concepto`** (`COMPRA` o `RENOVACION`), según la cotización la haya creado una renovación o no. Sirve para que los clientes distingan una renovación de una compra, por ejemplo para no ofrecer firmar el contrato de una póliza que ya existe.

### Ítem de `primas-pendientes`

| Campo | Significado |
| --- | --- |
| `tipo`, `accion` | Ver la tabla anterior |
| `referencia_id` | `renovacion_id` o `cotizacion_id` |
| `cotizacion_id` | La cotización que se paga con `POST /api/v1/pagos` (o cuyo contrato falta firmar) |
| `poliza_id`, `numero_poliza` | Solo en renovaciones |
| `ramo`, `nombre_ramo` | Código del ramo y el nombre que el cliente vio al cotizar |
| `monto`, `moneda` | Lo que se paga (o lo ya pagado, en `FIRMA_PENDIENTE`) |
| `fecha_limite` | Hasta cuándo se puede pagar; `null` en `FIRMA_PENDIENTE` |
| `mensaje` | Texto para el cliente, solo en `FIRMA_PENDIENTE` |

### Reglas del listado

- **Fecha límite de una renovación:** lo que ocurra primero entre el vencimiento de su cotización (7 días) y el fin de la póliza que renueva (las 23:59:59 de su último día, hora de Bogotá). Una renovación con la cotización vencida no se lista; se puede iniciar otra.
- **Fecha límite de una cotización:** su vencimiento. Si vence, deja de aparecer y hay que cotizar de nuevo.
- **Orden:** por fecha límite, la más próxima primero. Los ítems sin fecha límite van al final.
- **No aparecen:** renovaciones ya pagadas o de una póliza cancelada; cotizaciones vencidas, en borrador, ya pagadas o de otro cliente; contratos ya firmados. La cotización de una renovación no se repite como `COTIZACION`.
- **Pagos sin aplicar:** si un pago de renovación quedó aprobado pero el aviso falló, al listar se aplica y no se muestra como pendiente.
- Se calcula con las pólizas, cotizaciones, pagos, renovaciones y firmas que ya existen: **no agrega tablas**.

## Comprobante

Se genera al aprobarse cualquier pago, sea una compra o una renovación, y se guarda como registro propio.

| Campo | Significado |
| --- | --- |
| `comprobante_id`, `numero` | Identificador y número legible, como `CP-20261210-A1B2C3D4` (fecha del pago en Bogotá y el final del id del pago). Es estable: el mismo pago siempre da el mismo número |
| `pago_id`, `cotizacion_id` | De dónde sale |
| `concepto` | `COMPRA` o `RENOVACION` |
| `descripcion` | "Prima de Microseguro de vida" o "Renovación de la póliza SOL-2026-VIDA0001 (Microseguro de vida)" |
| `poliza_id`, `numero_poliza` | Solo en renovaciones; una compra aún no tiene póliza |
| `nombre_ramo`, `monto`, `moneda`, `metodo`, `referencia_pasarela` | Lo cobrado y cómo |
| `pagado_en`, `emitido_en` | Cuándo se pagó y cuándo se emitió el comprobante |

- **Idempotente:** hay una restricción única por pago, así que el aviso del pago y la consulta del cliente pueden coincidir sin duplicarlo.
- **Se recupera solo:** si el aviso del pago falló, el comprobante se genera la primera vez que se consulta.
- **Solo pagos aprobados:** un pago pendiente o rechazado responde 409 `PAGO_SIN_COMPROBANTE`. Un pago ajeno o inexistente responde 404.
- **Un fallo no frena a los demás:** el aviso del pago aprobado se reparte con `en_cadena`; si falla la aplicación de la renovación, el comprobante igual se genera, y al revés.
- La respuesta no incluye el `cliente_id`.

## Rechazos, reintentos y doble cobro

| Situación | Qué pasa |
| --- | --- |
| Pago rechazado | La prima sigue pendiente, la póliza no cambia, no hay comprobante. El cliente puede intentarlo de nuevo con otra `Idempotency-Key`, las veces que haga falta |
| Reintento con la misma llave y el mismo cuerpo (respuesta perdida, red caída) | Devuelve el mismo pago con 200 y **no vuelve a cobrar** ni a registrar otra transacción |
| Misma llave con otro cuerpo | 409 `LLAVE_IDEMPOTENCIA_REUTILIZADA`; no se cobra |
| Pago nuevo sobre algo ya pagado | 409 `COTIZACION_YA_PAGADA`; no se llama a la pasarela |
| Pasarela caída | El pago queda `PENDIENTE` y el reintento con la misma llave no cobra de nuevo |
| Pago aprobado cuyo aviso se perdió | El reintento devuelve el pago aprobado sin cobrar, y la renovación se aplica al listar las primas pendientes |

### Un solo pago aprobado por cotización

Además de la verificación del servicio, la base lo garantiza con un **índice único parcial** `uq_pagos_cotizacion_aprobado` sobre `pagos (cotizacion_id) WHERE estado = 'APROBADO'`. Así, dos solicitudes simultáneas que pasen la verificación a la vez no pueden dejar dos pagos aprobados.

Si un cobro aprobado por la pasarela llega cuando la cotización ya está pagada (por ejemplo, el cliente abre un pago PSE, paga con tarjeta y luego el banco confirma el PSE):

- El pago que llega tarde **queda `RECHAZADO`** con `motivo_rechazo = COBRO_DUPLICADO`; el que se aprobó primero se conserva.
- El servicio registra un error en el log (`Cobro duplicado: … Requiere devolución`) con ambos identificadores, para gestionar la devolución. **El sistema no mueve dinero.**

En una base que ya tenía la tabla de pagos, `preparar_esquema_registro` crea el índice al arrancar. Si ya hay cotizaciones con dos pagos aprobados, el índice no se puede crear: se registra `No se pudo crear uq_pagos_cotizacion_aprobado` y el servicio arranca igual. Esos casos hay que revisarlos a mano y reiniciar. Para encontrarlos:

```sql
SELECT cotizacion_id, COUNT(*) FROM pagos WHERE estado = 'APROBADO' GROUP BY cotizacion_id HAVING COUNT(*) > 1;
```

## Persistencia

- Tabla nueva `comprobantes` (se crea sola con `create_all`), con restricción única por `pago_id` y por `numero`.
- Índice nuevo en `pagos` (ver arriba). No cambian columnas de tablas existentes.

## Código

- Listado: `backend/app/polizas/primas_pendientes.py` (servicio), `backend/app/polizas/dominio/primas_pendientes.py` (modelos y orden), `backend/app/api/primas_pendientes.py` (API)
- Comprobante: `backend/app/pagos/comprobantes.py` (servicio), `backend/app/pagos/modelos.py` (`Comprobante`), `backend/app/pagos/repositorio_comprobantes.py`, endpoint en `backend/app/api/pagos.py`
- Doble cobro: `backend/app/pagos/modelos_db.py` (índice), `backend/app/pagos/repositorio.py` (`PagoAprobadoDuplicado`), `backend/app/pagos/servicio.py` (`COBRO_DUPLICADO`, `en_cadena`), `backend/app/infraestructura/database.py`

## Pruebas

`pytest tests/primas_pendientes tests/pagos` desde `backend`:

- `tests/primas_pendientes/` (24): los tres tipos, fecha límite, orden, exclusiones, pago sin aplicar y acceso.
- `tests/pagos/test_comprobantes.py` (18): compra y renovación, idempotencia, recuperación, cableado real con base de datos, API y el campo `concepto`.
- `tests/pagos/test_cobro_duplicado.py` (9): el índice en memoria y en base de datos, el cobro que llega tarde, y la creación del índice en bases existentes.
- `tests/pagos/test_reintentos_renovacion.py` (8): criterios 4 y 5 con una renovación — rechazo y nuevo intento, reintento sin doble cobro, pasarela caída y aviso perdido.

## Límites conocidos

- El comprobante es solo un registro para mostrar en pantalla; no hay PDF.
- Una cotización pagada no tiene número de póliza hasta firmar el contrato, y la firma solo está en el portal web.
- Un cobro duplicado queda registrado, pero la devolución es manual: no hay historia que la gestione.
- Un pago PSE que el cliente abandonó (queda `PENDIENTE`) no aparece como pendiente: la prima sigue en el listado y se puede pagar de nuevo.
- La firma del contrato no está en Android: el ítem `FIRMA_PENDIENTE` solo avisa que hay que firmar en el portal web.

## Clientes

No hay pantallas nuevas: la historia se resuelve con las que ya existían.

**Web**
- **Pagos:** sección "Pendientes de pago" (con "Pagar" o "Firmar contrato" según el ítem) y, en el historial, "Comprobante" en cada pago aprobado. El botón "Contrato" solo aparece mientras falta firmarlo.
- **Mis cotizaciones:** botón "Pagar" en las cotizaciones vigentes y con la oferta sin vencer.
- **Cotizar:** acepta `/cotizar?cotizacion=ID` y va directo al pago de esa cotización. La confirmación muestra el comprobante y, según el `concepto`, pide firmar el contrato (compra) o avisa que la póliza se renovó.

**Android**
- **Pagos:** sección "Pendientes de pago" con su botón "Pagar" (la pantalla de pago existente muestra el monto antes de confirmar), la tarjeta de aviso para el contrato por firmar y "Ver comprobante" en los pagos aprobados, que se abre como diálogo.
- **Confirmación del pago:** muestra el comprobante y pide firmar el contrato en el portal web. Si el pago fue de una renovación (HU22), también cuando se paga desde "Pagos pendientes", termina en "Póliza renovada" con el número del comprobante y "Ver póliza renovada" lleva a esa póliza.
- **Detalle de una cotización del historial:** "Aceptar y continuar" lleva al pago.

La fecha límite de una renovación es las 23:59:59 del último día de la póliza (hora de Bogotá), o antes si su cotización vence antes.

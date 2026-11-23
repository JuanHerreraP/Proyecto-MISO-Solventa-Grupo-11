# Renovación automática y facturación continua (HU17 / BPM-69)

## Qué hace

Renueva la póliza al terminar su vigencia sin que el cliente tenga que hacer trámites. Se apoya en la renovación de HU22 ([ciclo de vida de la póliza](ciclo-vida-poliza.md)): misma propuesta, misma cotización de renovación y mismo pago. Lo nuevo es **quién la dispara y cuándo**:

| Criterio | Cómo se cumple |
| --- | --- |
| Alerta de vencimiento | 30 días antes del vencimiento se envía un correo de preaviso con la prima de la renovación recalculada con la tarifa y el perfil de riesgo vigentes. |
| Procesamiento de la renovación | El día del vencimiento, si el cliente no desactivó la renovación automática, se crea la renovación y se cobra con la tarjeta registrada. |
| Actualización del contrato | Con el pago aprobado la póliza toma la nueva vigencia; se emite el documento contractual del nuevo periodo y se envía por correo al cliente. |

Aplica a los mismos ramos que HU22: vida, protección de dispositivos y paramétrico. El seguro de viaje no se renueva.

## Flujo

La tarea diaria (`ServicioRenovacionAutomatica.ejecutar`) recorre las pólizas no canceladas que vencen en los próximos 30 días:

1. **Preaviso (desde 30 días antes).** Una sola vez por periodo. Calcula la propuesta de HU22 y envía el correo con la vigencia nueva, la prima actual, la prima de la renovación, si la renovación automática está activa y la tarjeta registrada (últimos dígitos). Si la póliza ya no se puede renovar (p. ej. `RIESGO_NO_ASEGURABLE`), el ciclo queda `NO_RENOVABLE` y no se avisa un precio.
2. **Cobro (último día de la vigencia).**
   - Desactivada → no se crea nada (`DESACTIVADA`). El cliente puede renovar manualmente con HU22.
   - Activa sin tarjeta → se crea la renovación pendiente de pago (aparece en *Pagos* como prima pendiente, HU21) y se avisa al cliente (`SIN_MEDIO_DE_PAGO`).
   - Activa con tarjeta → se cobra la cotización de la renovación con `ServicioPagos` (el mismo del pago manual, con su comprobante).
3. **Resultado del cobro.**
   - Aprobado → la renovación se aplica (`RENOVADA`), se genera el PDF del nuevo periodo, se guarda con su huella SHA-256 y se envía por correo como adjunto.
   - Rechazado → `COBRO_RECHAZADO` y aviso al cliente. No se reintenta con la misma tarjeta.
   - Pasarela sin respuesta → `COBRO_PENDIENTE` hasta que llegue la confirmación.
4. **Seguimiento.** En cada ejecución se revisan los ciclos abiertos aunque la póliza ya haya vencido, mientras la cotización de la renovación siga vigente (7 días):
   - un pago confirmado después (webhook) o pagado a mano por el cliente concluye la renovación y envía el contrato;
   - una tarjeta nueva registrada tras un rechazo o sin tarjeta se cobra;
   - un contrato cuyo correo falló se reenvía;
   - si la cotización vence sin pago, el ciclo se cierra (`NO_PAGADA`).

### Estados del ciclo

| Estado | Significa |
| --- | --- |
| `PREAVISADA` | Se envió el preaviso; aún no llega el vencimiento. |
| `DESACTIVADA` | El cliente desactivó la renovación automática. |
| `SIN_MEDIO_DE_PAGO` | Activa pero sin tarjeta: la renovación queda pendiente de pago manual. |
| `COBRO_PENDIENTE` | La pasarela no respondió; se espera la confirmación. |
| `COBRO_RECHAZADO` | La tarjeta fue rechazada; se espera otra tarjeta o el pago manual. |
| `NO_RENOVABLE` | La póliza ya no cumple las reglas de renovación (motivo en `motivo`). |
| `NO_APLICADA` | Se cobró pero la renovación no se aplicó (p. ej. se canceló la póliza). Queda para devolución. |
| `NO_PAGADA` | La cotización de la renovación venció sin pago. |
| `RENOVADA` | Cobrada y aplicada; el contrato se emitió y se envió. |

## Endpoints

| Método y ruta | Quién | Qué hace |
| --- | --- | --- |
| `GET /api/v1/polizas/{poliza_id}/renovacion-automatica` | Cliente titular o asesor de la venta | Estado: `activa`, `tarjeta` (solo `ultimos_digitos`), `vence_el`, `preaviso_desde`, `cobro_programado_para` y `ultimo_ciclo`. |
| `PUT /api/v1/polizas/{poliza_id}/renovacion-automatica` | Cliente titular o asesor de la venta | Cuerpo `{"activa": bool, "tarjeta": {"token_tarjeta", "ultimos_digitos"}?, "quitar_tarjeta": bool?}`. Sin `tarjeta` se conserva la registrada. Solo el cliente registra o quita la tarjeta (403 `ACCESO_DENEGADO` para el asesor). 409 `RAMO_NO_RENOVABLE` en viaje. |
| `GET /api/v1/polizas/{poliza_id}/renovacion-automatica/{renovacion_id}/documento` | Cliente titular o asesor de la venta | PDF del periodo renovado, con `X-Huella-Documento`. 404 `RENOVACION_NO_ENCONTRADA`. |
| `POST /api/v1/operaciones/renovaciones-automaticas/ejecuciones` | `SERVICIO_INTERNO` | Ejecuta la tarea a demanda y devuelve el resumen (`preavisos`, `renovadas`, `contratos_enviados`, `rechazadas`, `errores`, …). |

Ejemplo de respuesta del `GET`:

```json
{
  "poliza_id": "POL-…",
  "disponible": true,
  "activa": true,
  "tarjeta": {"ultimos_digitos": "4242"},
  "vence_el": "2026-12-31",
  "preaviso_desde": "2026-12-01",
  "cobro_programado_para": "2026-12-31",
  "actualizado_en": "2026-11-19T13:00:00Z",
  "ultimo_ciclo": null
}
```

## Seguridad y reglas

- **Activa por defecto.** Sin registro de preferencia, la renovación automática está activa y sin tarjeta.
- **Nunca se guarda el número de la tarjeta**: solo el token de la pasarela y los últimos cuatro dígitos. Un valor con forma de número de tarjeta se rechaza con 422 y el error no repite lo enviado. El token nunca se devuelve en la API.
- **Idempotencia.** Un ciclo por periodo (`AUT-{poliza_id}-{AAAAMMDD}`, restricción única `poliza_id` + `vence_el`). El cobro usa una `Idempotency-Key` derivada de la cotización y de la huella del token: repetir la tarea no cobra dos veces; una tarjeta nueva sí genera un intento nuevo. El preaviso y el contrato registran su envío y no se repiten.
- **Fallos aislados.** Un error en una póliza se registra y no detiene las demás; la tarea sale con código 1 si hubo errores.
- El documento del nuevo periodo complementa el documento original de la póliza, que no se modifica (los documentos son inmutables). Conserva número y código de verificación (QR).
- La renovación creada por la tarea queda atribuida al rol `SERVICIO_INTERNO` (`SISTEMA-RENOVACION-AUTOMATICA`).
- El correo se toma del módulo de identidad al momento del envío, así que llega al correo actual del cliente.

## Configuración y cómo probar en local

La tarea se ejecuta una vez al día:

```bash
cd backend
python -m app.polizas.tarea_renovacion_automatica
```

En AWS se programa como tarea de ECS con EventBridge Scheduler sobre la misma imagen del backend (mismas variables de entorno que el servicio), con el comando anterior. Para una demo, el endpoint de operaciones ejecuta la misma tarea.

En el portal web, en **Mis pólizas** → detalle de una póliza de vida, dispositivos o paramétrica, aparece la sección *Renovación automática*: interruptor para activarla o desactivarla, registro de la tarjeta (se tokeniza en el navegador; una tarjeta terminada en 0 simula fondos insuficientes) y el resultado del último periodo con la descarga del documento renovado.

Los correos usan el adaptador simulado `CorreoRenovacionSimulado`, que los escribe en el log con nivel WARNING (`[CORREO SIMULADO] Preaviso de renovación …`).

## Pruebas

`backend/tests/renovacion_automatica/`:

- `test_dominio.py`: ventana de preaviso, día del cobro, ciclo por periodo y llave de cobro.
- `test_servicio.py`: los tres criterios, idempotencia de la tarea, desactivada, sin tarjeta, tarjeta rechazada y nueva tarjeta, pasarela caída y confirmación posterior, pago manual, reintento del envío del contrato, preferencias y documento.
- `test_api.py`: preferencia, tarjeta sin exponer el token, rechazo de un número en claro, permisos del asesor, documento y endpoint de operaciones.
- `test_repositorio.py`: persistencia de preferencias y ciclos, y pólizas por vencer en SQLite.

Web: `web/src/services/renovacion-automatica.service.test.ts` y `web/src/components/poliza/RenovacionAutomatica.test.tsx`.

## Pendientes conocidos

- Los correos son simulados (log); falta el adaptador de SES o SMTP.
- La tokenización de la tarjeta es simulada en el navegador, como en el pago de HU13.
- La programación diaria en AWS (EventBridge) no está en la plantilla de infraestructura; hoy se ejecuta con el comando o con el endpoint de operaciones.
- Una renovación cobrada pero no aplicable no devuelve el dinero: solo queda registrada (igual que en HU22).

## Código

- Dominio: `backend/app/polizas/dominio/renovacion_automatica.py`
- Caso de uso: `backend/app/polizas/renovacion_automatica.py` (reutiliza `ServicioRenovaciones.iniciar_automatica` y `propuesta_para`)
- Repositorio: `backend/app/polizas/repositorio_renovacion_automatica.py`; tablas `preferencias_renovacion_automatica` y `ciclos_renovacion_automatica` (se crean con `create_all`)
- Documento: `generar_pdf_renovacion` en `backend/app/polizas/pdf.py`
- Correos: `backend/app/polizas/comunicaciones.py`
- API: `backend/app/api/renovacion_automatica.py`
- Tarea: `backend/app/polizas/tarea_renovacion_automatica.py`
- Web: `web/src/components/poliza/RenovacionAutomatica.tsx`

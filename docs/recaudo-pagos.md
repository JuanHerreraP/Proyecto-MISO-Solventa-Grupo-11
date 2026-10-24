# Recaudo inicial de la prima (HU13)

## Qué hace

El cliente asegurado paga la prima de una cotización vigente con tarjeta (token de la pasarela) o con PSE. El backend registra el pago, lo cobra a través de una pasarela y recibe la confirmación final por un webhook firmado. Cobra una sola vez aunque el cliente o la red reintenten.

La pasarela incluida es **simulada** (`app/pagos/pasarela_simulada.py`). El resto del módulo depende del puerto `PasarelaPagos`, de modo que se puede cambiar por el proveedor real sin tocar el servicio.

## Flujo

1. El cliente envía `POST /api/v1/pagos` con `Idempotency-Key`.
2. El servicio valida que la cotización exista, sea del cliente, esté vigente y no tenga un pago aprobado.
3. Se crea el pago en `PENDIENTE` y se llama a la pasarela:
   - **Tarjeta:** responde `APROBADO` o `RECHAZADO` en el momento.
   - **PSE:** queda `PENDIENTE` y se devuelve `url_redireccion`; el estado final llega por el webhook.
   - **Pasarela caída:** el pago queda `PENDIENTE` y responde 502. Se reintenta con la misma llave.
4. La pasarela notifica a `POST /api/v1/pagos/confirmaciones` con el resultado.

## Endpoints

| Método y ruta | Quién | Devuelve |
|---|---|---|
| `POST /api/v1/pagos` | Cliente | `201` con el pago; `200` si es un reintento idempotente |
| `GET /api/v1/pagos/{pago_id}` | Cliente, solo sus pagos | Estado del pago |
| `POST /api/v1/pagos/confirmaciones` | Pasarela (sin sesión, con firma) | `{pago_id, estado}` |

**Cuerpo de `POST /api/v1/pagos`:** `cotizacion_id`, `metodo` (`TARJETA` o `PSE`), `token_tarjeta` (tarjeta), `codigo_banco` (PSE) y `url_retorno` opcional.

**Cuerpo de la confirmación:** `referencia`, `estado` (`APROBADO` o `RECHAZADO`) y `motivo` opcional. Debe llevar el encabezado `X-Firma-Pasarela` con el HMAC-SHA256 del cuerpo exacto, usando `PAGOS_WEBHOOK_SECRET`.

### Códigos de respuesta

| Código | Cuándo |
|---|---|
| 401 | Firma de la confirmación ausente o inválida |
| 403 | Quien paga no es un cliente |
| 404 | Cotización o pago inexistente, o ajeno (no se revela que existe) |
| 409 | `COTIZACION_NO_VIGENTE`, `COTIZACION_YA_PAGADA` o `LLAVE_IDEMPOTENCIA_REUTILIZADA` |
| 422 | Falta el token (tarjeta) o el banco (PSE), falta la `Idempotency-Key`, o se envió un número de tarjeta |
| 502 | `PASARELA_NO_DISPONIBLE`; el pago queda pendiente |

## Estados del pago

| Estado | Significado |
|---|---|
| `PENDIENTE` | Esperando a la pasarela o a la confirmación |
| `APROBADO` | Cobro exitoso; la cotización queda asociada al pago |
| `RECHAZADO` | Cobro fallido; la cotización sigue vigente y se puede intentar de nuevo |

`APROBADO` y `RECHAZADO` son finales: una confirmación repetida o contradictoria no los cambia.

## Seguridad y reglas

- **Idempotencia:** la llave es única por cliente (`uq_pagos_cliente_llave`). Se guarda una huella SHA-256 del cuerpo; la misma llave con otro cuerpo devuelve 409.
- **Firma del webhook:** HMAC-SHA256 comparado en tiempo constante. Sin firma o con firma distinta responde 401.
- **Sin datos de tarjeta:** solo se recibe el token de la pasarela. Si el valor parece un PAN (13 a 19 dígitos), se rechaza con 422.
- **Errores 422 sin eco:** en las rutas de pagos se omite el valor recibido (`input`, `ctx`) para no devolver un posible número de tarjeta.
- **Un pago aprobado por cotización:** no se puede pagar dos veces.

## Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `PAGOS_WEBHOOK_SECRET` | Ninguno (obligatoria) | Secreto compartido con la pasarela para firmar las confirmaciones. Si falta, la confirmación falla con error de configuración |

Genera un valor con `python -c "import secrets; print(secrets.token_hex(32))"`. Debe ser el mismo en Solventa y en la pasarela, y distinto entre desarrollo y producción.

## Cómo probar en local

La pasarela simulada decide el resultado según el token:

| Entrada | Resultado |
|---|---|
| `token_tarjeta` que empieza por `tok_rechazado` | `RECHAZADO` (`FONDOS_INSUFICIENTES`) |
| `token_tarjeta` que empieza por `tok_caido` | 502, pago `PENDIENTE` |
| Cualquier otro token de tarjeta (8 caracteres o más) | `APROBADO` |
| `metodo: PSE` | `PENDIENTE` con `url_redireccion`; confirmar por el webhook |

Para simular la confirmación, firma el cuerpo JSON con el mismo secreto y envíalo con `X-Firma-Pasarela`.

## Pruebas

`pytest tests/pagos` desde `backend` (`tests/pagos/test_pagos.py`, 16 casos): pago aprobado y rechazado, idempotencia y conflicto de llave, doble pago, número de tarjeta en claro, cotización ajena o vencida, rol no cliente, pasarela caída, flujo PSE, confirmaciones repetidas o contradictorias, firma inválida y pago desconocido.

## Pendientes conocidos

- La pasarela es simulada; falta integrar el proveedor real y su formato de firma.
- Aún no hay cliente web ni Android para el pago.
- No se emite la póliza al aprobarse el pago (HU12).

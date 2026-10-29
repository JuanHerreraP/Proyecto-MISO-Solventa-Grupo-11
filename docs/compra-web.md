# Comprar un seguro desde la web: cotizar, aceptar y pagar (HU23)

## Qué hace

Desde el portal web el cliente recorre en una sola pantalla el flujo de compra: elige el ramo, llena los datos de riesgo, obtiene la cotización, la acepta y paga la prima inicial. Reutiliza los servicios de cotización (HU03) y de recaudo (HU13); esta HU aporta la experiencia web que los une de principio a fin.

## Flujo

La pantalla `CotizarPage` avanza por pasos: `ramo → formulario → resultado → pago → confirmación`.

1. **Ramo:** el cliente elige entre viaje, dispositivos, vida o paramétrico.
2. **Formulario:** se piden los campos de riesgo del ramo (catálogo de HU03) y se envía `POST /api/v1/cotizaciones`.
3. **Resultado:** se muestra la prima y el detalle; el cliente **acepta** o cancela.
4. **Pago:** al aceptar se genera una `Idempotency-Key` y se paga con tarjeta o PSE (`POST /api/v1/pagos`, HU13).
5. **Confirmación:** aprobado, rechazado (con opción de reintentar) o pendiente (PSE, por webhook).

## Servicios que consume

| Paso | Llamada |
|---|---|
| Catálogo de ramos y campos | `GET /api/v1/cotizaciones/ramos` |
| Crear cotización | `POST /api/v1/cotizaciones` |
| Consultar cotización | `GET /api/v1/cotizaciones/{id}` |
| Pagar la prima | `POST /api/v1/pagos` con `Idempotency-Key` |
| Consultar el pago | `GET /api/v1/pagos/{id}` |

El detalle de cada API está en [Perfil de riesgo y pricing (HU11)](perfil-de-riesgo.md) y [Recaudo inicial de la prima (HU13)](recaudo-pagos.md).

## Reglas y seguridad

- Todas las llamadas van autenticadas con el token de la sesión web; el `cliente_id` sale del token.
- El pago usa una `Idempotency-Key` única por intento: un reintento tras un rechazo genera una llave nueva para no chocar con el cobro anterior.
- PSE queda `PENDIENTE` y su estado final llega por el webhook firmado de la pasarela.
- La pasarela es simulada (desarrollo); el resultado depende del token de prueba, igual que en HU13.


## Pruebas

- Backend: `pytest tests/cotizaciones` y `pytest tests/pagos` cubren las APIs que consume el flujo.
- Web: `npm test` (Vitest) en `web/`.



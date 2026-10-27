# Siniestros: registro manual y detección paramétrica (HU20)

## Qué hace

El cliente asegurado registra un siniestro sobre una de sus pólizas vigentes desde la app Android, y además Solventa detecta siniestros de forma **automática** cuando un proveedor externo de telemetría (vuelos, clima) reporta un evento que supera el umbral contratado de una póliza paramétrica. En ambos casos la lista de siniestros del cliente se consulta desde la app.

El proveedor de telemetría es un servicio aparte y deliberadamente pequeño: informa una observación y la empuja a Solventa; **no** consulta pólizas, no compara umbrales, no decide siniestros ni conoce al cliente. Solventa es quien decide.

## Endpoints

| Método y ruta | Quién | Devuelve |
|---|---|---|
| `POST /api/v1/siniestros` | Cliente | `201` con el siniestro registrado manualmente |
| `GET /api/v1/siniestros` | Cliente | Sus siniestros, del más reciente al más antiguo (manuales y automáticos) |
| `POST /api/v1/integraciones/telemetria/eventos` | Proveedor externo (X-API-Key) | `201` si se creó un siniestro, `200` si no hay cobertura o el evento ya se procesó |

**Cuerpo de `POST /api/v1/siniestros`:** `poliza_id`, `fecha_evento`, `hora_evento`, `lugar`, `descripcion` (mín. 10) y `estimacion_danos`. El `cliente_id` sale de la sesión, nunca del cuerpo.

**Cuerpo del evento de telemetría:** `evento_id`, `tipo_evento` (`RETRASO_VUELO` o `EVENTO_CLIMATICO`), `valor_observado`, `fecha_evento` y, según el tipo, `numero_vuelo` o `ubicacion`.

### Códigos de respuesta

| Código | Cuándo |
|---|---|
| 401 | Token ausente o inválido (cliente); `X-API-Key` ausente o inválida (telemetría) |
| 403 | La póliza no pertenece al cliente, o el rol no es cliente |
| 404 | La póliza no existe |
| 409 | La póliza no está vigente |
| 422 | Fecha futura o fuera de la vigencia, o datos inválidos |

## Flujo paramétrico

1. El proveedor simula un evento (`POST /simulate/flight-delay` o `/simulate/weather-event`), genera un `evento_id` único y lo empuja a Solventa con `X-API-Key`.
2. Solventa busca pólizas paramétricas vigentes que apliquen (por `numero_vuelo` o `ubicacion`), compara `valor_observado` con el umbral contratado y, si lo alcanza, crea un siniestro `AUTOMATICO`.
3. La idempotencia es por `evento_id`: reenviar el mismo evento no duplica el siniestro.

La condición contratada vive en `cobertura_principal.descripcion` como pares `clave=valor` (por ejemplo `tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG; umbral_disparo=180; unidad=MINUTOS`), los mismos códigos del catálogo de cotización.

## Seguridad

- **Cliente:** el access token no sale del `AuthCoordinator` hacia la UI; la app lo pide por `SesionAutenticada`. Un 401 cierra la sesión. El backend filtra por la identidad del token: la app nunca envía el identificador del cliente.
- **Telemetría:** comunicación `sistema → sistema` con `X-API-Key` (no JWT de usuario), credencial leída de variable de entorno. Queda preparada para sustituirse por OAuth Client Credentials o API Gateway.
- El proveedor nunca decide la cobertura: solo informa el valor observado.

## Configuración (proveedor de telemetría)

| Variable | Por defecto | Uso |
|---|---|---|
| `SOLVENTA_TELEMETRY_URL` | `http://localhost:8000/api/v1/integraciones/telemetria/eventos` | A dónde empuja el evento |
| `SOLVENTA_TELEMETRY_API_KEY` | `solventa-telemetry-dev` | Credencial de servicio (`X-API-Key`) |

Cómo levantar el proveedor y disparar un evento: ver el README del repositorio.

## App Android

Desde el inicio o la pestaña **Siniestros** se abre «Mis siniestros» (`GET /api/v1/siniestros`), con etiquetas de origen (Automático/Manual) y estado. «Reportar siniestro» abre un formulario con selector de póliza, fecha y hora (pickers nativos), lugar, descripción y estimación, y registra vía `POST /api/v1/siniestros`.

## Pruebas

- Backend: `pytest tests/siniestros` (servicio y API del registro manual, y la integración de telemetría: sin cobertura, sobre umbral, idempotencia y auth por `X-API-Key`) y `pytest tests/telemetry` (el proveedor externo).
- Android: `./gradlew testDebugUnitTest` incluye `SiniestrosCoordinatorTest`, `RemoteSiniestrosGatewayTest`, `SiniestroFormValidationTest` y `CondicionParametricaTest`.


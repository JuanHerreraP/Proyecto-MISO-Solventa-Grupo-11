# Notificaciones push (HU05)

## Qué hace

Solventa avisa al cliente, en la app Android, de tres tipos de eventos:

| Tipo | Cuándo | Al tocarla |
|---|---|---|
| `PAGO_PARAMETRICO` | Se aprueba automáticamente el pago de un seguro paramétrico. Dice el monto y la póliza. | Abre el detalle de ese siniestro |
| `ESTADO_SINIESTRO` | Un siniestro cambia de estado (registrado, en evaluación, aprobado, rechazado). | Abre el detalle de ese siniestro, ya actualizado |
| `VENCIMIENTO_POLIZA` | Una póliza renovable vence en **15** o en **3** días. | Abre el flujo de renovación de esa póliza |

Reglas que cumple:

- **Siempre queda registrado.** Cada evento se guarda en la bandeja del cliente aunque el push esté deshabilitado, no haya teléfono registrado o FCM falle. El push es solo el aviso; la bandeja es el registro.
- **Agrupación.** Los eventos del mismo tipo del mismo día (hora de Bogotá) comparten una notificación en el teléfono: el primero llega normal y los siguientes la reemplazan por un resumen ("Tienes 3 pagos nuevos…"). En la bandeja cada evento sigue siendo una fila propia.
- **Preferencia.** El cliente apaga o enciende el push desde Perfil → Notificaciones. Sin preferencia guardada, el push está activado.
- **Idempotencia.** Cada evento tiene una clave (por ejemplo `PAGO_PARAMETRICO:<siniestro>`); repetirlo no duplica la notificación ni el push.

Es solo para la app móvil; la web no consume esta función.

## Cómo funciona

```
Evento de negocio ──► ServicioNotificaciones ──► bandeja (BD)
 (siniestro aprobado,       │
  cambio de estado,         └─ ¿push habilitado y con teléfonos? ──► canal de push ──► FCM ──► teléfono
  job de vencimientos)
```

- **Disparadores** (en el backend, dentro del flujo que ya existía):
  - `ServicioEvaluacion` (siniestros): al decidir un siniestro, `APROBADO` + `AUTOMATICO` genera `PAGO_PARAMETRICO`; cualquier otro cambio genera `ESTADO_SINIESTRO`.
  - `ServicioVencimientos`: job diario que avisa las pólizas **renovables y vigentes** que vencen exactamente en 15 y en 3 días.
- **Un fallo de notificación nunca rompe el flujo de negocio.** Aprobar un siniestro no depende de que el push salga.
- **Canal de push** (`app/notificaciones/canal.py`): `EnviadorPushFCM` envía de verdad por la API HTTP v1 de Firebase (un envío por token; los tokens que FCM marca como no registrados se dan de baja solos); `EnviadorPushSimulado` solo escribe en el log.
- **Etiqueta de agrupación:** `tipo` + día. Viaja como `tag` de la notificación de Android, y una notificación con la misma etiqueta reemplaza a la anterior.
- **Privacidad:** el push usa visibilidad `PRIVATE` (en la pantalla de bloqueo no se ve el contenido) y los motivos de rechazo no viajan en el aviso; el cliente los ve en el detalle.

## Endpoints

Todos exigen el access token y rol **CLIENTE**; el backend filtra por la identidad del token, la app nunca manda el identificador del cliente.

| Método y ruta | Devuelve |
|---|---|
| `GET /api/v1/notificaciones?limite=&desplazamiento=` | La bandeja, la más reciente primero (`limite` 1-100, por defecto 50), con `no_leidas` |
| `GET /api/v1/notificaciones/no-leidas` | Solo el conteo, para la insignia de la campana |
| `POST /api/v1/notificaciones/{id}/leida` | Marca una como leída (repetirlo no cambia nada) y devuelve cuántas quedan sin leer |
| `PUT /api/v1/notificaciones/dispositivos` | `204`. Registra el token de push del teléfono (`token`, `plataforma`). Es un upsert: el mismo token siempre apunta al último cliente que lo registró |
| `POST /api/v1/notificaciones/dispositivos/baja` | `204`. Da de baja el token (cierre de sesión). Tolerante: un token desconocido no falla |
| `GET` / `PUT /api/v1/notificaciones/preferencias` | `{ "push_habilitado": bool }` |
| `POST /api/v1/internos/notificaciones/vencimientos?fecha=` | **Interno.** Header `X-Clave-Interna`. Corre el job de vencimientos; `fecha` (opcional) lo corre como si fuera ese día |

Errores del job: `401 CLAVE_INVALIDA` si la clave no coincide y `503 JOB_NO_CONFIGURADO` si no hay clave configurada (no existe una clave por defecto). Los `422` de las rutas de dispositivos no devuelven el token en el detalle del error.

### Datos que lleva el push

El push de un evento individual lleva estas claves en `data`, y la app las usa para decidir el destino (también llegan como extras del intent cuando Firebase muestra el aviso en segundo plano):

| Clave | Contenido |
|---|---|
| `tipo` | `PAGO_PARAMETRICO`, `ESTADO_SINIESTRO` o `VENCIMIENTO_POLIZA` |
| `notificacion_id` | Para marcarla como leída al abrirla |
| `siniestro_id` | En los dos tipos de siniestro |
| `poliza_id` | En el vencimiento y en los de siniestro |

El resumen agrupado lleva solo `tipo` y `notificacion_id`: no tiene destino propio y abre la bandeja.

## Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `FCM_CREDENCIALES_PATH` | — | Ruta del JSON de la cuenta de servicio de Firebase (desarrollo local) |
| `FCM_CREDENCIALES_JSON` | — | Contenido del JSON de la cuenta de servicio (producción: viene de Secrets Manager) |
| `PUSH_PROVEEDOR` | automático | `fcm` o `simulado`. Sin valor: FCM si hay credencial configurada y simulado si no. `simulado` gana sobre la credencial; `fcm` sin credencial válida queda como error en el log al arrancar |
| `NOTIFICACIONES_CLAVE_INTERNA` | — | Clave del job de vencimientos (mínimo 32 caracteres). Sin ella el endpoint responde 503 |

La cuenta de servicio y el `google-services.json` de la app deben ser del **mismo proyecto de Firebase**; si no, FCM rechaza el envío con `SENDER_ID_MISMATCH`. La credencial de la cuenta de servicio es un secreto: no se sube al repositorio. El `google-services.json` (`android/app/`) sí va versionado.

### Producción (AWS)

- `infra/aws/stack.json` inyecta `FCM_CREDENCIALES_JSON` y `NOTIFICACIONES_CLAVE_INTERNA` a la tarea desde el secreto de aplicación (`fcm_credenciales_json` y `notificaciones_clave_interna`). El workflow **AWS Infra** los toma de los secrets de GitHub del mismo nombre; ambos son opcionales.
- Con la clave interna definida, el stack crea una regla de **EventBridge** (`cron(0 13 * * ? *)`, las 08:00 de Colombia) que llama cada día al endpoint del job con el header `X-Clave-Interna`. El job es idempotente: reintentos o ejecuciones repetidas el mismo día no duplican avisos.
- La clave llega a EventBridge al **crear o actualizar el stack**. Si se cambia el secreto, hay que volver a desplegar para que la regla use la nueva.
- Si se pierde un día de ejecución, se recupera con `?fecha=` del día perdido.

## App Android

- **Bandeja** (`NotificationsScreen`): lista con las no leídas marcadas, estado vacío y de error con reintento. La campana de Inicio muestra la insignia con el conteo.
- **Detalle de siniestro** (`ClaimDetailScreen`): progreso del caso con sus pasos. Se llega desde la lista de siniestros o desde una notificación, y se vuelve a pedir al backend cada vez que se abre.
- **Perfil → Notificaciones:** interruptor del push. Al activarlo se pide el permiso `POST_NOTIFICATIONS` (Android 13 o más); si está bloqueado en el sistema se ofrece "Permitir" o "Abrir ajustes". Si no se puede guardar, el interruptor vuelve a como estaba.
- **Teléfono registrado:** `ProveedorTokenFcm` pide el token a Firebase; se registra al iniciar sesión y se da de baja **antes** de cerrar la sesión (con un tope de 3 s para que el cierre nunca se quede esperando). Si Firebase renueva el token con la sesión abierta, `SolventaMessagingService` lo registra.
- **Notificación en el teléfono:** con la app en segundo plano la muestra Firebase; con la app abierta la muestra `SolventaMessagingService`, con la misma etiqueta de agrupación. Canal `solventa_notificaciones`, creado al arrancar la app.
- **Abrir el destino:** `MainActivity` es `singleTop`. La apertura (`AperturaNotificacion`) queda pendiente hasta que haya sesión de cliente y el usuario esté en una pantalla privada; entonces `NavGraph` navega y marca la notificación como leída. Si el destino no está disponible, cae a la bandeja o a Inicio.
- **Solo clientes:** asesores y servicio interno no ven la bandeja ni la campana, porque los endpoints son de cliente.

## Pruebas

- **Backend:** `backend/tests/notificaciones/` (bandeja, repositorios, servicio, canal, FCM contra un transporte falso, endpoints, job y agrupación). Un envío real nunca ocurre en las pruebas: sin credencial, el canal es el simulado.
- **Android:** pruebas unitarias del coordinador, del gateway (MockWebServer), de los destinos, de los intents y de las pantallas (Robolectric y Compose). Se corren con `./gradlew testDebugUnitTest` desde `android/`.
- **Prueba manual con un push real** (emulador con Google Play Services):
  1. Dejar la credencial de Firebase en una ruta local fuera del repo y levantar el backend con `FCM_CREDENCIALES_PATH` apuntando a ella.
  2. Iniciar sesión como cliente en el emulador y activar el push en Perfil.
  3. Disparar un evento. El paramétrico completo: sembrar pólizas con `CLIENTE_EMAIL=<correo> python sembrar_polizas.py` y empujar un retraso de vuelo con el simulador de telemetría (`POST /simulate/flight-delay`, ver [Siniestros](siniestros.md)).
  4. Comprobar con la app abierta, en segundo plano y cerrada que la notificación llega y abre el destino. Con el push apagado, que el evento aparece en la bandeja sin aviso.

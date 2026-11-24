# Pago paramétrico por eventos: SNS, SQS y consumidor idempotente

## Qué hace

Cuando se aprueba automáticamente un siniestro paramétrico, Siniestros **publica un evento** en un tópico de Amazon SNS en lugar de ordenar el pago en el mismo proceso. SNS lo reparte a una cola SQS de pagos, y un worker de Cobros y Pagos lo consume y ordena el desembolso **cuando tiene capacidad**.

Así, un pico de eventos de telemetría no se convierte en un pico de pagos contra la red de desembolsos, y un reintento o un mensaje duplicado no puede pagar dos veces.

```
Telemetría ─► Cola de telemetría ─► Worker de telemetría ─► Siniestros
                                                              │ aprueba, avisa al cliente (HU05)
                                                              │ y publica SINIESTRO_PARAMETRICO_APROBADO
                                                              ▼
                                                        Tópico SNS ──► Cola de pagos ──► Worker de pagos ──► Desembolso
                                                                          │ 5 intentos
                                                                          ▼
                                                                    Cola de fallidos (DLQ) ──► alarma
```

La aprobación **manual** de Operaciones (HU15) no cambia: sigue ordenando el desembolso en línea, porque es una acción puntual de una persona que espera su resultado.

## El evento

| Campo | Contenido |
|---|---|
| `evento_id` | `PAGO_PARAMETRICO:<siniestro_id>`. Se deriva del siniestro, no se genera al azar |
| `tipo` | `SINIESTRO_PARAMETRICO_APROBADO` |
| `ocurrido_en` | Cuándo se aprobó |
| `datos` | `siniestro_id`, `cliente_id`, `poliza_id`, `monto_aprobado` y `moneda` |

Como el identificador es estable, publicar dos veces el mismo hecho (un reintento o el barrido de pendientes) produce el mismo evento, y el consumidor lo reconoce como repetido.

La suscripción de la cola usa entrega cruda (`RawMessageDelivery`) y un filtro por el atributo `tipo`: solo llegan a la cola de pagos los eventos de ese tipo.

## Idempotencia: dos barreras

1. **Eventos procesados.** Antes de pagar, el consumidor pregunta a la tabla `eventos_procesados` si ese evento ya se procesó para su consumidor (`pagos`). Si es así, lo omite.
2. **Un desembolso por siniestro.** La tabla `desembolsos` tiene una restricción única por siniestro. Aunque dos consumidores lean el mismo evento a la vez, o el evento llegue con otro identificador, el segundo recibe el mismo desembolso y no paga otra vez.

El evento se marca como procesado **solo después de pagar**:

| Resultado del desembolso | Qué hace el consumidor |
|---|---|
| Completado | Marca el evento y borra el mensaje |
| Pendiente (la red de desembolsos no respondió) | **No** marca el evento y falla: SQS reentrega el mensaje |
| Fallido (por ejemplo, cuenta inexistente) | Lo registra, marca el evento y borra el mensaje. Operaciones lo reintenta desde su bandeja cuando el cliente corrija su cuenta |
| El siniestro del evento no existe | Falla: tras los reintentos el mensaje acaba en la DLQ |

## Reintentos y cola de fallidos

El worker borra un mensaje **solo si lo procesó bien**. Los demás vuelven a la cola al vencer el tiempo de visibilidad (120 s) y, tras 5 intentos, SQS los envía a la DLQ. Una alarma de CloudWatch (`PagosDlqAlarm`) pasa a `ALARM` cuando hay mensajes en la DLQ, y se ve en la consola de CloudWatch. No envía notificaciones: no hay un destino de avisos configurado. Es el momento de que Operaciones revise esos siniestros, desde `POST /api/v1/operaciones/siniestros/{id}/desembolso/reintento`.

## Barrido de pendientes

Guardar la aprobación y publicar el evento no son una sola operación. Si SNS no responde justo después de aprobar, el siniestro queda **aprobado sin desembolso**. Para no depender de que alguien lo note, el worker de pagos hace un barrido cada cierto tiempo y vuelve a publicar el evento de:

- los siniestros paramétricos aprobados sin desembolso, y
- los desembolsos que siguen pendientes porque la red no respondió y los reintentos de la cola se agotaron,

siempre que lleven más de `PAGOS_BARRIDO_ANTIGUEDAD` segundos sin actividad. Publicar de más es inocuo por la idempotencia.

## Variables de entorno

| Variable | Dónde | Por defecto | Efecto |
|---|---|---|---|
| `SNS_TOPIC_ARN` | API, worker de telemetría y worker de pagos | (vacío) | Tópico de eventos. **Sin ella, el sistema conserva el comportamiento síncrono**: la aprobación automática ordena el desembolso en el mismo proceso. Es el modo de desarrollo local y de las pruebas |
| `EC_ORDENAR_DESEMBOLSO` | worker de telemetría | `false` | `true` aprueba el siniestro paramétrico y avisa al cliente. Con `SNS_TOPIC_ARN`, además publica el pago; sin ella, lo ordena en línea. En AWS vale `true` |
| `SQS_PAGOS_QUEUE_URL` | worker de pagos | (obligatoria) | Cola de pagos |
| `PAGOS_WORKER_CONCURRENCIA` | worker de pagos | `4` | Pagos procesados en paralelo por tarea |
| `PAGOS_BARRIDO_SEGUNDOS` | worker de pagos | `300` | Cada cuánto corre el barrido |
| `PAGOS_BARRIDO_ANTIGUEDAD` | worker de pagos | `300` | Segundos sin actividad para que un pago cuente como pendiente |
| `SOLVENTA_ROL` | worker de pagos | `api` | `worker-pagos` arranca el consumidor en lugar de la API (ver `entrypoint.py`) |

## Infraestructura (`infra/aws/stack.json`)

| Recurso | Para qué |
|---|---|
| `EventosNegocioTopic` | Tópico SNS de eventos de negocio |
| `PagosQueue` y `PagosDlq` | Cola de pagos (espera larga de 20 s, 120 s de visibilidad, 5 intentos) y su cola de fallidos |
| `PagosQueuePolicy` | Permite que **solo ese tópico** escriba en la cola |
| `PagosSubscription` | Suscripción con entrega cruda y filtro por `tipo` |
| `PagosWorkerService` y `PagosWorkerTask` | Servicio de Fargate (256 CPU y 512 MB) que ejecuta el worker. Su rol solo puede leer la cola de pagos y publicar en el tópico |
| `PagosDlqAlarm` | Alarma por mensajes en la DLQ |

Parámetros: `PagosWorkerDesiredCount` (0 detiene los pagos y la cola crece) y `PagosWorkerConcurrencia`.

El tópico no usa cifrado propio de SNS: el evento lleva identificadores y un monto, sin datos personales. Las dos colas declaran el cifrado administrado de SQS (`SqsManagedSseEnabled`).

### Aprovisionar y eliminar

- El workflow **AWS Infra** crea todo con el stack. Después del despliegue **verifica** que el tópico tenga su suscripción confirmada a la cola de pagos, y avisa si el worker no tiene tareas. Si cambia un secreto, reinicia la API **y los dos workers**.
- Al **eliminar**, el workflow anota el tópico y las colas antes de borrar el stack y, después, **comprueba que no quede nada**: si algún recurso sobrevivió (un borrado interrumpido, por ejemplo), lo elimina. Las colas, el tópico, la suscripción y la alarma no tienen política de retención: se borran con el stack. Ver `infra/aws/DESPLIEGUE.md`.

## Cómo probarlo

1. Con el stack desplegado, dispara un evento de telemetría que cubra una póliza paramétrica (ver [Siniestros](siniestros.md)).
2. El siniestro queda **aprobado** de inmediato, y el cliente recibe el aviso del pago (HU05).
3. Segundos después el desembolso aparece **completado**. Mira los logs del servicio `PagosWorkerService`.
4. Reenvía el mismo evento desde la consola de SNS: el desembolso no se duplica y el log dice "ya procesado".

Los reintentos por una red caída, la cuenta fallida y el barrido se prueban con pruebas automáticas, porque la red de desembolsos simulada de AWS no tiene un interruptor.

## Pruebas automáticas

`backend/tests/eventos/` (modelo, publicador SNS y eventos procesados) y `backend/tests/desembolsos/test_pagos_asincronos.py` (publicación, consumidor, barrido, worker y armado del servicio). Cubren los casos de arriba: pago único con un mensaje repetido, red caída, cuenta fallida, siniestro inexistente, fallo de SNS y barrido.

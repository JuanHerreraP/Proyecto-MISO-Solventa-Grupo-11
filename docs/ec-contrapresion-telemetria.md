# Contrapresión con Amazon SQS para telemetría paramétrica (HU20)

Experimento de calidad: absorber ráfagas de eventos de telemetría externa sin
perder mensajes ni tumbar el backend. El endpoint deja de procesar en línea y
pasa a **aceptar y encolar**; un worker drena la cola a un ritmo acotado. La
contrapresión queda expresada en la profundidad de la cola: si llegan más
eventos de los que el worker puede procesar, la cola crece de forma visible y el
sistema sigue aceptando sin degradarse; al subir la capacidad del worker la cola
se vacía sin pérdida.

## Arquitectura

```
Proveedor de telemetría
        │  POST /api/v1/integraciones/telemetria/eventos  (X-API-Key)
        ▼
  Backend (ECS Service "backend")
        │  valida el cuerpo y publica a SQS (PublicadorSQS.SendMessage)
        │  202 Accepted solo si SQS devolvió MessageId; 503 si rechazó
        ▼
  SQS  TelemetriaQueue  ──(maxReceiveCount=5)──▶  TelemetriaDlq
        │  ReceiveMessage (long polling 20s, hasta 10 por lote)
        ▼
  Worker (ECS Service "WorkerService", misma imagen, SOLVENTA_ROL=worker)
        │  ThreadPoolExecutor acotado por EC_WORKER_CONCURRENCIA
        │  cada mensaje: Session propia -> ServicioTelemetria.procesar()
        │  DeleteMessage SOLO si el procesamiento fue exitoso
        ▼
  RDS PostgreSQL (SiniestroDB, índice único uq_siniestros_evento por evento_id)
```

Piezas de código:

- `backend/app/siniestros/cola.py` — `PublicadorEventos` (interfaz), `PublicadorSQS`, `PublicadorEnMemoria`.
- `backend/app/api/telemetria.py` — ingesta: valida, publica, responde 202/503.
- `backend/app/siniestros/worker.py` — loop de consumo con concurrencia acotada.
- `backend/app/siniestros/metricas.py` — métricas CloudWatch tolerantes a fallos.
- `backend/app/siniestros/conciliacion.py` y `backend/reconciliar_telemetria.py` — conciliación.
- `infra/aws/stack.json` — `TelemetriaQueue`, `TelemetriaDlq`, IAM, `WorkerService`.

### Por qué contrapresión y no procesamiento en línea

Procesar en línea acopla la tasa de ingesta a la latencia de RDS y del
desembolso: una ráfaga satura el pool de conexiones y empieza a devolver 5xx,
con pérdida de eventos. Con la cola, la ingesta solo valida y publica (operación
barata y acotada), y el trabajo pesado se difiere. SQS retiene hasta que el
worker pueda; la profundidad de la cola es el amortiguador.

### Idempotencia y reintentos

- La idempotencia es por `evento_id`: `SiniestroDB` tiene el índice único
  `uq_siniestros_evento` y `RepositorioSiniestrosPostgres.guardar` captura el
  `IntegrityError`. Un `evento_id` repetido (reintento de SQS, doble publicación)
  produce resultado `DUPLICADO`, nunca un segundo siniestro.
- El worker borra el mensaje (`DeleteMessage`) **solo** si el procesamiento
  terminó bien. Si falla, no se borra: SQS lo reentrega tras el
  `VisibilityTimeout` y, superado `maxReceiveCount=5`, lo mueve a la DLQ. Así
  ningún evento se pierde en silencio.

### Desembolso desacoplado

En el worker el desembolso es configurable con `EC_ORDENAR_DESEMBOLSO`
(default `false`). En `false` el worker llama a `ServicioTelemetria` con
`al_crear=None`: crea el siniestro pero **no** ordena desembolso ni marca pago.
En `true` usa `construir_evaluacion(db).aprobar_automatico`: aprueba el siniestro y avisa
al cliente. Sin `SNS_TOPIC_ARN` ordena además el desembolso en el mismo proceso. Con
`SNS_TOPIC_ARN` **publica el pago como evento** y lo ordena un worker aparte, a su ritmo
(ver [Pago paramétrico por eventos](mensajeria-pagos.md)). En AWS el worker corre con `true`.
El default conservador evita disparar pagos automáticos durante una prueba de carga.

## Variables de entorno

| Variable | Dónde | Default | Efecto |
|---|---|---|---|
| `SQS_QUEUE_URL` | backend y worker | (vacío) | URL de `TelemetriaQueue`. Si está definida, el endpoint usa `PublicadorSQS`; si no, `PublicadorEnMemoria` (local/tests). El worker la necesita siempre. |
| `AWS_DEFAULT_REGION` | backend y worker | (de ECS) | Región para boto3 (SQS, CloudWatch). |
| `EC_MODO_SINCRONO` | backend | `false` | `true` conserva el procesamiento en línea anterior (compatibilidad / tests existentes). `false` publica a la cola. |
| `EC_WORKER_CONCURRENCIA` | worker | `4` | Eventos procesados en paralelo. **Palanca de contrapresión**: bajarlo reduce la tasa de drenaje. |
| `EC_ORDENAR_DESEMBOLSO` | worker | `false` | `true` aprueba el siniestro al crearlo. Con `SNS_TOPIC_ARN` publica el pago; sin ella lo ordena en línea. |
| `EC_METRICAS` | backend y worker | `true` | `false` desactiva el envío de métricas a CloudWatch. |
| `SOLVENTA_ROL` | ambos contenedores | (vacío=API) | `worker` arranca el loop de consumo en lugar de uvicorn (ver `entrypoint.py`). |
| `SOLVENTA_TELEMETRY_API_KEY` | backend | `solventa-telemetry-dev` | Clave del header `X-API-Key` del endpoint de ingesta. |

## Métricas y profundidad de cola

`backend/app/siniestros/metricas.py` publica en el namespace
**`Solventa/Telemetria`**:

- `EventosRecibidos` — en la ingesta/publicador, uno por evento aceptado.
- `EventosProcesados` — en el worker, por evento procesado con éxito.
- `EventosFallidos` — en el worker, por evento que lanzó excepción.

El envío es tolerante a fallos: si CloudWatch no responde, se registra en log y
el flujo continúa. Se apaga con `EC_METRICAS=false`.

**La profundidad de cola no se publica como métrica propia.** SQS ya expone
nativamente, sin código, las métricas de CloudWatch:

- `ApproximateNumberOfMessagesVisible` — pendientes por procesar (lo que crece bajo contrapresión).
- `ApproximateNumberOfMessagesNotVisible` — en vuelo (recibidos, aún no borrados).
- Las mismas métricas sobre la DLQ miden los que agotaron reintentos.

Se consultan en CloudWatch (namespace `AWS/SQS`, dimensión `QueueName`) o con
`aws sqs get-queue-attributes`.

## Build / push / deploy

El patrón es el de [infra/aws/DESPLIEGUE.md](../infra/aws/DESPLIEGUE.md); el
worker reusa la **misma imagen** del backend, así que no hay build adicional.

```bash
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1

# 1) Construir y subir la imagen (igual que el backend, DESPLIEGUE.md paso 1).
export BACKEND_REPO=$(aws cloudformation describe-stacks --stack-name solventa-ecr \
  --query "Stacks[0].Outputs[?OutputKey=='BackendUri'].OutputValue" --output text)
export REGISTRY="${BACKEND_REPO%%/*}"
aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"
export IMAGE_TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
docker build -t "$BACKEND_REPO:$IMAGE_TAG" backend
docker push "$BACKEND_REPO:$IMAGE_TAG"

# 2) Regenerar parameters.json (DESPLIEGUE.md paso 3.3) con el nuevo IMAGE_TAG.
#    Opcional: fijar la contrapresión del worker.
#    {'ParameterKey': 'WorkerConcurrencia', 'ParameterValue': '4'}
#    {'ParameterKey': 'WorkerDesiredCount', 'ParameterValue': '1'}

# 3) Validar y desplegar.
#    Nota: la plantilla supera 51200 bytes, por lo que validate-template inline ya no
#    aplica (ValidationError por tamaño). Validar el esquema completo offline con cfn-lint:
#      pip install cfn-lint && cfn-lint infra/aws/stack.json
#    o subir la plantilla a S3 y validar con --template-url.
aws cloudformation deploy --stack-name solventa-mvp \
  --template-file infra/aws/stack.json \
  --parameter-overrides file://infra/secrets/parameters.json \
  --capabilities CAPABILITY_IAM

# 4) Ver las salidas nuevas.
aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query "Stacks[0].Outputs[?OutputKey=='QueueUrl' || OutputKey=='DlqUrl' || OutputKey=='WorkerService']" \
  --output table
```

El backend y el worker leen `DB_PASSWORD` de Secrets Manager; ECS relee secretos
al iniciar cada tarea, así que un cambio de parámetros del worker fuerza tareas
nuevas automáticamente.

## Cómo demostrar la contrapresión

Idea: provocar que la ingesta supere la capacidad del worker, ver crecer la cola
sin errores de ingesta, y luego ampliar el worker y ver vaciarse sin pérdida.

1. **Reducir la capacidad de drenaje.** Dejar el worker casi detenido:

   ```bash
   # Opción A: una sola tarea con concurrencia 1.
   aws cloudformation deploy --stack-name solventa-mvp --template-file infra/aws/stack.json \
     --parameter-overrides WorkerConcurrencia=1 WorkerDesiredCount=1 ... \
     --capabilities CAPABILITY_IAM
   # Opción B: detener el drenaje por completo.
   #   WorkerDesiredCount=0
   ```

2. **Inyectar carga** con el plan JMeter (`backend/tests/jmeter/`). La ingesta
   sigue respondiendo 202: valida y publica, no procesa.

3. **Observar crecer la cola.** En CloudWatch (`AWS/SQS` →
   `ApproximateNumberOfMessagesVisible`) o:

   ```bash
   export QUEUE_URL=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
     --query "Stacks[0].Outputs[?OutputKey=='QueueUrl'].OutputValue" --output text)
   aws sqs get-queue-attributes --queue-url "$QUEUE_URL" \
     --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
   ```

   La cola crece; la ingesta no devuelve 5xx. Eso es la contrapresión: el backlog
   absorbe la ráfaga.

4. **Ampliar el worker** (subir `WorkerConcurrencia` y/o `WorkerDesiredCount`) y
   volver a desplegar. `ApproximateNumberOfMessagesVisible` baja hasta 0.

5. **Comprobar que no hubo pérdida** con la conciliación (abajo): los aceptados
   deben igualar procesados + en cola + en DLQ.

## Conciliación (no se pierde nada)

`backend/reconciliar_telemetria.py` imprime los conteos de la cola principal
(`ApproximateNumberOfMessages`, `...NotVisible`), de la DLQ, y los siniestros con
origen `TELEMETRIA` en la BD. Reusa la construcción de `DATABASE_URL` igual que
`crear_admin.py`.

Invariante a demostrar:

```
aceptados (EventosRecibidos)
  == procesados (SINIESTRO_CREADO + SIN_COBERTURA + DUPLICADO)
   + en_cola (visible + no visible)
   + en_dlq
```

```bash
cd backend
export SQS_QUEUE_URL=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query "Stacks[0].Outputs[?OutputKey=='QueueUrl'].OutputValue" --output text)
export SQS_DLQ_URL=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query "Stacks[0].Outputs[?OutputKey=='DlqUrl'].OutputValue" --output text)
# DB_HOST / DB_PASSWORD como en crear_admin.py.
python reconciliar_telemetria.py
```

En reposo (cola y DLQ en 0), los siniestros de origen `TELEMETRIA` deben
coincidir con los eventos únicos aceptados. Si quedan en DLQ, son los que
agotaron sus 5 reintentos: ahí se diagnostica, no se pierden.

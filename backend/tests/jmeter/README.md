# Prueba de carga JMeter — telemetría paramétrica (HU20)

`telemetria_1M.jmx` hace `POST` al endpoint de ingesta de eventos de telemetría
para ejercer la contrapresión con SQS. Cada request lleva un `evento_id` **único**
(`LOAD-${__UUID()}`), de modo que todos los eventos son distintos y, en condiciones
normales, cada uno debería producir un siniestro (o `SIN_COBERTURA`), nunca `DUPLICADO`.

> No ejecutar contra el MVP de demo sin querer: 1.000.000 de requests generan
> carga real en SQS, RDS y Fargate. Arrancar con un volumen pequeño.

## Qué envía

- Método/ruta: `POST {BASE_URL}/api/v1/integraciones/telemetria/eventos`
- Cabeceras: `Content-Type: application/json`, `X-API-Key: {API_KEY}`
- Cuerpo (un `evento_id` único por request):

  ```json
  {
    "evento_id": "LOAD-<uuid>",
    "tipo_evento": "EVENTO_CLIMATICO",
    "ubicacion": "BOG",
    "valor_observado": 200,
    "fecha_evento": "2026-10-26T18:00:00Z"
  }
  ```

- Aserción: código `202` (publicó a SQS) o `200` (modo síncrono `EC_MODO_SINCRONO=true`).

## Ejecutar (modo no-GUI) y generar reporte HTML

```bash
jmeter -n -t telemetria_1M.jmx -l resultados.jtl -e -o reporte/
```

- `-n` sin GUI, `-t` plan, `-l` fichero de resultados, `-e -o reporte/` genera el
  dashboard HTML en `reporte/` (el directorio debe estar vacío o no existir).

## Parametrizar

Todo se pasa con `-J` (propiedades JMeter). Valores por defecto entre paréntesis:

| Propiedad | Default | Qué controla |
|---|---|---|
| `BASE_URL` | `http://localhost:8000` | Base del backend (p. ej. la salida `Url` de CloudFront). |
| `API_KEY` | `solventa-telemetry-dev` | Valor del header `X-API-Key` (`SOLVENTA_TELEMETRY_API_KEY`). |
| `HILOS` | `200` | Hilos (usuarios virtuales) concurrentes. |
| `DURACION_SEG` | `600` | Duración total (10 minutos). |
| `THROUGHPUT_POR_MIN` | `100020` | Ritmo objetivo por minuto (referencia; ver nota). |

Ejemplo apuntando al despliegue:

```bash
MVP_URL=$(aws cloudformation describe-stacks --stack-name solventa-mvp \
  --query "Stacks[0].Outputs[?OutputKey=='Url'].OutputValue" --output text)

jmeter -n -t telemetria_1M.jmx -l resultados.jtl -e -o reporte/ \
  -JBASE_URL="$MVP_URL" \
  -JAPI_KEY="$SOLVENTA_TELEMETRY_API_KEY" \
  -JHILOS=400 \
  -JDURACION_SEG=600
```

## 1.000.000 de requests en 10 minutos → requiere JMeter distribuido

1.000.000 / 600 s ≈ **1667 req/s** sostenidos. Un solo nodo JMeter rara vez
sostiene ese ritmo contra un endpoint remoto (CPU, sockets, red del generador).
El plan trae un *Constant Throughput Timer* configurado a 100.020 req/min como
referencia, pero el timer solo **limita hacia arriba**: alcanzarlo depende de
tener suficientes hilos y suficiente capacidad de generación.

Para llegar a 1667 req/s hay que repartir la carga en varios nodos
(*distributed testing*): un controlador y N *workers* ejecutando el mismo plan.
Con M nodos, cada uno apunta a ~`1667/M` req/s (baja `THROUGHPUT_POR_MIN` por nodo
en consecuencia) y los resultados se agregan en el controlador:

```bash
# En cada worker:
jmeter-server
# En el controlador:
jmeter -n -t telemetria_1M.jmx -R worker1,worker2,worker3,worker4 \
  -l resultados.jtl -e -o reporte/ \
  -JBASE_URL="$MVP_URL" -JAPI_KEY="$SOLVENTA_TELEMETRY_API_KEY"
```

Como la ingesta solo valida y publica a SQS (trabajo barato y acotado), el cuello
de botella bajo contrapresión es el **drenaje del worker**, no la ingesta: la cola
crecerá (`ApproximateNumberOfMessagesVisible`) mientras los 202 siguen fluyendo.
Ver cómo observarlo y conciliar en
[`docs/ec-contrapresion-telemetria.md`](../../../docs/ec-contrapresion-telemetria.md).

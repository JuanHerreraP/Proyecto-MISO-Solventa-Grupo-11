# Emisión de la póliza y entrega de su documento (HU12)

## Qué hace

Cuando el cliente completa la firma electrónica del contrato (HU14), el backend emite la póliza de forma automática, compila el documento PDF con los datos del asegurado, la cobertura, la tarifa cobrada y los sellos de la firma, y lo guarda una sola vez junto con su huella SHA-256. El portal muestra el mensaje de éxito con la descarga inmediata del PDF. Después de responder, y sin demorar al cliente, se envían el correo de bienvenida con el PDF adjunto y la confirmación al cliente.

El correo y la notificación usan un adaptador **simulado** (`app/polizas/comunicaciones.py`): registran el envío en el log y no salen del proceso. El almacenamiento usa un adaptador de **disco** (`app/polizas/almacenamiento.py`). Ambos están detrás de puertos (`EnviadorCorreo`, `Notificador`, `AlmacenDocumentos`), así que pasar a SES o a S3 es escribir otro adaptador sin tocar la emisión.

## Flujo

1. El cliente firma (`POST /api/v1/firmas/{cotizacion_id}/firma`). Al guardar la firma, `ServicioFirmas` llama al emisor.
2. `ServicioEmision.emitir` exige un proceso de firma `FIRMADA` y crea la póliza con lo contratado y lo cobrado: titular, cobertura, prima del pago, vigencia y un código de verificación.
3. Genera el PDF (`app/polizas/pdf.py`), lo escribe en el almacén sin permitir que se sobrescriba y registra su huella SHA-256 en `documentos_poliza`.
4. La respuesta de la firma incluye `poliza_id`. El portal ofrece **Descargar póliza (PDF)**.
5. Como tarea en segundo plano se envían el correo de bienvenida y la confirmación. Cada uno se marca como enviado y no se repite.

## Garantías

- **Idempotente.** El identificador de la póliza (`POL-<uuid de la cotización>`) y su número se derivan de la cotización, y el PDF es determinista. Repetir la firma, un doble clic o una respuesta perdida no duplican la póliza, el documento ni el correo.
- **La firma no depende de la emisión.** Si la emisión falla, la firma se conserva y el error queda en el log. Repetir la firma o consultar el contrato ya firmado completa la emisión pendiente.
- **Documento inmutable.** El almacén rechaza sobrescribir una clave con otro contenido y, al descargar, se compara el archivo con la huella registrada. Si no coinciden, responde 409 `DOCUMENTO_ALTERADO`.
- **El correo no bloquea.** Si falla, la póliza sigue emitida y el envío queda pendiente para el próximo intento.

## Vigencia

- Viaje y paramétrico: las fechas `fecha_inicio` y `fecha_fin` declaradas al cotizar.
- Con `meses_cobertura` o `plazo_meses` (por ejemplo, vida hipotecario): desde la fecha de la firma, hora de Colombia, por ese número de meses.
- En cualquier otro caso: un año desde la firma.

## Endpoint

| Método y ruta | Quién | Qué hace |
| --- | --- | --- |
| `GET /api/v1/polizas/{poliza_id}/documento` | Cliente titular o asesor de la venta asistida | Devuelve el PDF (`application/pdf`, `attachment`). La huella SHA-256 viaja en `X-Huella-Documento`. |

Respuestas: 404 si la póliza no existe o es de otro cliente; 403 si el asesor no participó en esa venta, o si el actor es otro rol o un socio; 409 si el documento fue alterado; 503 si el almacén no responde. La respuesta de la firma (`RespuestaFirma`) incluye `poliza_id`, que es `null` hasta que la póliza queda emitida.

## Configuración

| Variable | Uso |
| --- | --- |
| `POLIZAS_DOCUMENTOS_DIR` | Carpeta de los PDF (por defecto `./documentos_polizas`). En AWS el disco del contenedor no es persistente: hay que escribir el adaptador de S3 antes de desplegar. |

## Pruebas

- `backend/tests/emision/`: emisión, idempotencia, PDF, descarga por cliente y asesor, integridad, correo y notificación asíncronos, y repositorios de base de datos.
- `web/src/pages/FirmaPage.test.tsx` y `web/src/services/poliza-documento.service.test.ts`: mensaje de éxito, descarga, reintento y póliza en preparación.

## Pendiente

- Adaptador de S3 para el almacenamiento y de SES (o SMTP) para el correo.
- El envío en segundo plano usa las tareas de FastAPI. Un fallo deja el envío pendiente, pero nada lo reintenta solo: una cola con reintentos (SQS, como en la arquitectura) es el siguiente paso.
- Vista de pólizas del asesor en el portal. El endpoint ya permite su descarga.

# Reporte de siniestro con evidencias desde Android (HU04 / EC10)

## Qué hace

El cliente asegurado reporta un siniestro desde la app Android con el tipo de siniestro y adjunta fotos o videos tomados con la cámara o elegidos de la galería. Cada captura queda con su huella SHA-256, la fecha y hora y, si el cliente autoriza la ubicación, la latitud y longitud. Si se pierde la conexión, el reporte y las evidencias se guardan como borrador en el teléfono y se envían después sin duplicar el siniestro ni las evidencias.

Las evidencias son inmutables y cada carga, consulta, descarga o falla de integridad queda en una bitácora de auditoría con autor, rol, IP y fecha (escenario de calidad EC10).

Historia: [BPM-27](https://proyecto-miso-grupo-11.atlassian.net/browse/BPM-27). Escenario de calidad: [BPM-84](https://proyecto-miso-grupo-11.atlassian.net/browse/BPM-84). Amplía el registro manual de [HU20](siniestros.md).

## Flujo

1. El cliente abre **Reportar siniestro**. La app pide una vez el permiso de ubicación; si lo niega, puede continuar.
2. Elige la póliza, el tipo de siniestro, la fecha, la hora, el lugar, la descripción y la estimación.
3. Agrega fotos o videos (**Foto**, **Video** o **Galería**). Cada uno se guarda en la carpeta privada del borrador con su huella. Sin ubicación, la app avisa que la evidencia irá sin geoetiqueta; los archivos de la galería siempre van sin ubicación.
4. Al tocar **Registrar siniestro**:
   1. Se guarda el borrador con los datos del formulario.
   2. Se registra el siniestro (`POST /api/v1/siniestros`) con el id del borrador como `Idempotency-Key`.
   3. Se sube cada evidencia pendiente (`POST /api/v1/siniestros/{id}/evidencias`) y se marca como enviada al llegar.
   4. Con todo enviado, se elimina el borrador y se vuelve a la lista.
5. Sin conexión en cualquier paso, el borrador queda con el avance. Al volver a abrir el formulario se precarga; si el siniestro ya se registró, solo se envían las evidencias que faltan.

## Endpoints

| Método y ruta | Quién | Devuelve |
|---|---|---|
| `POST /api/v1/siniestros` | Cliente | `201` con el siniestro; `200` si se repite con la misma `Idempotency-Key` |
| `POST /api/v1/siniestros/{id}/evidencias` | Cliente titular | `201` con la evidencia; `200` si el mismo archivo ya estaba adjunto |
| `GET /api/v1/siniestros/{id}/evidencias` | Cliente titular, Operaciones/Siniestros, Analista de cumplimiento | Las evidencias en orden de carga |
| `GET /api/v1/siniestros/{id}/evidencias/{evidencia_id}/contenido` | Los mismos | El archivo, con su huella en `X-Huella-Evidencia` |
| `GET /api/v1/siniestros/{id}/evidencias/auditoria` | Operaciones/Siniestros, Analista de cumplimiento | La bitácora de auditoría del siniestro |

No hay endpoints para modificar ni borrar evidencias (`PUT` y `DELETE` responden 405).

**Registro (`POST /api/v1/siniestros`):** el cuerpo de HU20 más `tipo_siniestro` opcional: `DANO_MATERIAL`, `ROBO_HURTO`, `ACCIDENTE`, `ENFERMEDAD`, `FALLECIMIENTO`, `INCIDENTE_VIAJE`, `EVENTO_CLIMATICO` u `OTRO`. El encabezado `Idempotency-Key` (8 a 80 caracteres) es opcional; la clave no se devuelve en la respuesta.

**Carga de evidencia:** `multipart/form-data` con:

| Parte | Obligatoria | Descripción |
|---|---|---|
| `archivo` | Sí | Foto `image/jpeg` o `image/png` (hasta 10 MB), o video `video/mp4` o `video/3gpp` (hasta 50 MB) |
| `capturada_en` | No | ISO 8601 con zona horaria; se guarda en UTC |
| `latitud`, `longitud` | No | Juntas, en grados decimales |
| `precision_metros` | No | Solo con ubicación |

Encabezado opcional `X-Contenido-SHA256`: huella calculada por la app. Si no coincide con la del archivo recibido, la carga se rechaza.

### Códigos de respuesta

| Código | `codigo` | Cuándo |
|---|---|---|
| 403 | `ACCESS_DENIED` | Un rol distinto al cliente intenta adjuntar, o un rol sin acceso intenta consultar |
| 404 | `SINIESTRO_NO_ENCONTRADO` | El siniestro no existe o es de otro cliente |
| 404 | `EVIDENCIA_NO_ENCONTRADA` | La evidencia no existe o es de otro siniestro |
| 409 | `SINIESTRO_CERRADO` | El siniestro ya fue aprobado o rechazado |
| 409 | `LIMITE_EVIDENCIAS` | El siniestro ya tiene 10 evidencias |
| 409 | `EVIDENCIA_ALTERADA` | Al descargar, el archivo almacenado no coincide con su huella o ya no existe |
| 409 | `IDEMPOTENCY_KEY_REUTILIZADA` | La misma clave llegó con datos de otro siniestro |
| 413 | `ARCHIVO_DEMASIADO_GRANDE` | La foto supera 10 MB o el video 50 MB |
| 415 | `TIPO_NO_PERMITIDO` | Formato no admitido |
| 422 | `CONTENIDO_NO_COINCIDE` | La firma del archivo no corresponde al tipo declarado |
| 422 | `ARCHIVO_VACIO` | El archivo no tiene contenido |
| 422 | `HUELLA_NO_COINCIDE` | La huella enviada por la app no coincide con la del archivo |
| 422 | `FECHA_CAPTURA_INVALIDA` | La fecha de captura está más de 5 minutos en el futuro |
| 422 | `DATOS_CAPTURA_INVALIDOS` | Fecha sin zona o ubicación incompleta o fuera de rango |
| 503 | `ALMACEN_NO_DISPONIBLE` | No se pudo escribir ni leer el archivo |

## Integridad y auditoría (EC10)

- **Huella en el servidor.** El backend calcula el SHA-256 de cada archivo y lo compara con el que declara la app.
- **Archivo inmutable.** Se guarda una sola vez en `evidencias-siniestros/{siniestro_id}/{huella}.{ext}`, en el bucket de S3 de las pólizas con respaldo en disco. Escribir otra vez la misma clave con contenido distinto es un error.
- **Verificación en cada lectura.** Al descargar se recalcula la huella. Si no coincide o el archivo desapareció, se responde `EVIDENCIA_ALTERADA` y se registra `INTEGRIDAD_FALLIDA`.
- **Sin duplicados.** La tabla `evidencias_siniestro` tiene una restricción única por `(siniestro_id, huella_sha256)`; `siniestros` tiene otra por `(cliente_id, clave_idempotencia)`.
- **Bitácora.** La tabla `auditoria_evidencias_siniestro` registra `CARGA`, `CONSULTA`, `DESCARGA`, `INTEGRIDAD_FALLIDA` y `CONSULTA_AUDITORIA`, con el autor, su rol, la IP, el user agent y la fecha. La aplicación solo inserta filas en ella.

## App Android

- **Formulario** (`ClaimFormScreen`): selector de tipo de siniestro y sección de evidencias con contador, botones de foto, video y galería, y la lista de evidencias (pendiente o enviada, con o sin ubicación). Las pendientes se pueden quitar.
- **Captura** (`CapturaEvidencias.kt`): usa la cámara y el selector de fotos del sistema. La cámara escribe directo en la carpeta privada a través del `FileProvider` de la app, por lo que la app no necesita el permiso `CAMERA`.
- **Ubicación** (`ProveedorUbicacion`): última ubicación conocida de los proveedores activos, sin servicios de Google, solo con permiso concedido.
- **Borrador** (`BorradoresSiniestroArchivo`): uno por usuario en `files/borradores_siniestro/<sha256 del usuario>/`, con `borrador.json` y la carpeta `evidencias/`. Se excluye de los respaldos y de la transferencia entre dispositivos.
- **Reglas** (`SiniestrosCoordinator`): guardar el borrador antes de usar la red, registrar con `Idempotency-Key`, subir solo lo pendiente y eliminar el borrador al terminar.

## Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `SINIESTROS_EVIDENCIAS_DIR` | `./evidencias_siniestros` | Carpeta local de las evidencias (y respaldo cuando hay S3) |
| `POLIZAS_S3_BUCKET`, `POLIZAS_S3_PREFIJO`, `POLIZAS_S3_ENDPOINT_URL` | Sin valor | Las mismas del PDF de la póliza; con bucket, las evidencias van a S3 bajo `evidencias-siniestros/` |

El backend agrega la dependencia `python-multipart`. Las columnas `tipo_siniestro` y `clave_idempotencia` se agregan solas en bases existentes; las tablas nuevas se crean al iniciar.

## Cómo probar en local

1. Levanta el backend y la app como en HU20, e ingresa con un cliente que tenga una póliza vigente.
2. En el emulador, fija una ubicación en **Extended controls → Location** antes de tomar la foto; sin ella, la última ubicación conocida puede estar vacía.
3. Reporta un siniestro con una foto y un video. Verifica en `GET /api/v1/siniestros/{id}/evidencias` que quedaron con huella y `geoetiquetada`.
4. **Sin conexión:** activa el modo avión, toca **Registrar siniestro**, vuelve a abrir el formulario sin red y comprueba que el reporte sigue ahí. Desactiva el modo avión, registra otra vez y verifica que hay un solo siniestro con sus evidencias.
5. **Integridad:** modifica el archivo en `backend/evidencias_siniestros/` y descarga la evidencia como Operaciones: debe responder `409 EVIDENCIA_ALTERADA` y aparecer `INTEGRIDAD_FALLIDA` en la bitácora.

## Pruebas

- Backend: `pytest tests/siniestros` incluye `test_evidencias_servicio.py` (reglas, integridad y auditoría), `test_evidencias_api.py` (contrato HTTP) y `test_evidencias_repositorio.py` (persistencia, restricciones únicas y migración), además de los casos de tipo e idempotencia en `test_api.py`.
- Android: `./gradlew testDebugUnitTest` incluye `SiniestrosEvidenciasTest` (borrador, reintento sin duplicar y avisos de ubicación), `BorradoresSiniestroArchivoTest` (archivos privados por usuario), los casos de HU04 en `RemoteSiniestrosGatewayTest` (multipart, huella e `Idempotency-Key`) y `SiniestroFormValidationTest`.

## Límites conocidos

- Las fotos y videos del borrador no se cifran en el teléfono; viven en el almacenamiento privado de la app y se borran al enviarse o descartarse.
- La ubicación es la última conocida por el sistema; si el teléfono no la tiene, la evidencia se envía sin geoetiqueta.
- Las evidencias se adjuntan solo desde la app del cliente; el asesor no adjunta evidencias en el registro asistido.

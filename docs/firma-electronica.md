# Firma electrónica del contrato (HU14)

## Qué hace

Cuando el pago de la prima de una cotización queda `APROBADO` (HU13), el cliente asegurado revisa en el portal web el contrato prellenado con las condiciones particulares de su seguro y lo firma con un código OTP que recibe por SMS o por correo. Quedan registrados la fecha, la IP, el navegador, el firmante, la huella SHA-256 del documento y el sello del proveedor de firma. HU12 emite la póliza a partir de un contrato firmado.

El proveedor de firma incluido es **simulado** (`app/firmas/proveedor_simulado.py`): no envía SMS ni correos, deja el código en el log del backend. El servicio depende solo del puerto `ProveedorFirmaElectronica`, así que el proveedor real se conecta escribiendo otro adaptador, sin tocar el servicio (EC06).

Los dos últimos criterios de la historia en Jira (aprobación de siniestros por Operaciones y prohibición al cliente de generar desembolsos) pertenecen a HU15 y no se implementan aquí.

## Flujo

1. Desde **Pagos**, en un pago aprobado, el cliente abre **Contrato** (`/firma/{cotizacion_id}`).
2. `GET /api/v1/firmas/{cotizacion_id}` arma el contrato la primera vez: titular, cobertura, datos del riesgo, prima pagada, referencia del pago y cláusulas del ramo. El nombre del ramo es el mismo del catálogo de cotización (por ejemplo, "Microseguro de vida"). Si la cotización de vida trae `valor_credito`, el contrato es de vida hipotecario y agrega la cláusula de la entidad financiera como beneficiaria. Lo guarda tal cual y fija su huella. Las consultas siguientes devuelven el mismo documento aunque cambien los datos del cliente.
3. El cliente marca la autorización, elige SMS o correo y pide el código (`POST .../otp`).
4. El cliente escribe el código. El portal envía el código y la huella del contrato que revisó (`POST .../firma`).
5. El servicio verifica que la huella coincida, que el contrato guardado no haya sido alterado, que el pago siga aprobado y que el código sea válido. Luego pide el sello al proveedor y guarda la firma.

## Endpoints

Todos exigen sesión de un usuario con rol `CLIENTE` y solo operan sobre sus propias cotizaciones.

| Método y ruta | Devuelve |
|---|---|
| `GET /api/v1/firmas/{cotizacion_id}` | El proceso de firma con el contrato, su huella y el estado del OTP |
| `POST /api/v1/firmas/{cotizacion_id}/otp` | Envía un código. Cuerpo: `{"canal": "SMS" \| "EMAIL"}` |
| `POST /api/v1/firmas/{cotizacion_id}/firma` | Firma. Cuerpo: `{"codigo": "123456", "huella_documento": "<sha256>"}` |

La respuesta nunca incluye el OTP ni su hash. Incluye `estado`, `contrato`, `huella_documento`, `documento_integro`, el destino enmascarado del código, su vencimiento, `intentos_restantes`, `envios_restantes`, `reenvio_disponible_en` y, cuando está firmado, `firmado_en`, `ip_firmante` y `referencia_proveedor`.

Repetir la firma de un contrato ya firmado (por ejemplo, tras perder la respuesta) devuelve la firma existente sin volver a sellar.

### Códigos de respuesta

| Código | Cuándo |
|---|---|
| 401 | Sin sesión |
| 403 | Quien firma no es un cliente |
| 404 | `COTIZACION_NO_ENCONTRADA` o `FIRMA_NO_ENCONTRADA`: no existe o es de otro cliente (no se revela cuál) |
| 409 | `PAGO_NO_APROBADO`, `TITULAR_SIN_DATOS`, `COTIZACION_INCOMPLETA`, `DOCUMENTO_ALTERADO`, `ENVIOS_AGOTADOS`, `YA_FIRMADO` |
| 422 | `OTP_INCORRECTO`, `OTP_VENCIDO`, `OTP_NO_EMITIDO`, `OTP_INTENTOS_AGOTADOS`, `DESTINO_NO_DISPONIBLE`, o formato inválido |
| 423 | `FIRMA_BLOQUEADA` |
| 429 | `ESPERA_REENVIO`: se pidió otro código antes de 30 segundos |
| 503 | `PROVEEDOR_FIRMA_NO_DISPONIBLE` |

Los errores de negocio llegan en `detail` con `codigo` y `mensaje`; los del OTP agregan `intentos_restantes`, `envios_restantes` y `reenvio_disponible_en`.

## Estados

| Estado | Significado |
|---|---|
| `PENDIENTE` | Contrato presentado, sin firmar |
| `FIRMADA` | Firmado y sellado; final |
| `BLOQUEADA` | Se agotaron los tres códigos con sus tres intentos; requiere intervención del asesor |

## Reglas y seguridad

- **Solo después del pago:** no se presenta ni se firma un contrato sin pago `APROBADO` de esa cotización y de ese cliente. Se vuelve a verificar al firmar.
- **OTP:** 6 dígitos generados con `secrets`, válidos 5 minutos, 3 intentos por código. Hasta 3 envíos por proceso, con 30 segundos entre envíos. Un código nuevo invalida el anterior.
- **El código no se guarda:** se guarda su HMAC-SHA256 con `FIRMA_OTP_SECRET`, y se compara en tiempo constante. Tras firmar se borra el hash.
- **Huella del documento (EC10):** SHA-256 de la serialización canónica del contrato (JSON con claves ordenadas). El cliente envía la huella del contrato que revisó; si no coincide con la guardada, o si el contrato guardado ya no produce esa huella, la firma se rechaza con `DOCUMENTO_ALTERADO`.
- **Metadatos de la firma:** fecha, firmante, IP (`request.client.host`), navegador (`User-Agent`), referencia y sello del proveedor.
- **Proveedor caído:** pedir el código o sellar responde 503 sin consumir envíos ni intentos; se puede reintentar con el mismo código mientras esté vigente.
- **Errores 422 sin eco:** en las rutas de firma se omite el valor recibido para no devolver el código.
- **Auditoría:** todas las rutas de `/api/v1/firmas` quedan en el log de operaciones sensibles.
- **Un proceso por cotización:** la tabla `firmas_contrato` tiene `cotizacion_id` único; dos peticiones simultáneas terminan usando el mismo proceso.

## Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `FIRMA_OTP_SECRET` | Llave aleatoria del proceso | Llave del HMAC de los OTP. Obligatoria en AWS: sin ella, con varias tareas ECS un código emitido por una tarea no se valida en otra, y los códigos se pierden al reiniciar |

Genera un valor con `python -c "import secrets; print(secrets.token_hex(32))"`.

## Cómo probar en local

1. Levanta el backend y la web como indica el [README](../README.md#backend-en-local).
2. Ten una cotización con pago aprobado (con la pasarela simulada, cualquier `token_tarjeta` de 8 caracteres o más que no empiece por `tok_rechazado` ni `tok_caido`).
3. En la web, entra a **Pagos** y abre **Contrato** en el pago aprobado.
4. Marca la autorización y pide el código. El código aparece en la consola del backend:

   ```
   [FIRMA SIMULADA] OTP 927699 para 3001234567 por SMS (proceso FIR-...)
   ```

5. Escribe el código y firma.

## Pruebas

- Backend, desde `backend`: `pytest tests/firmas` (41 casos). Contrato prellenado y estable, sin pago aprobado, cliente ajeno, titular sin datos, envío por SMS y correo, espera y límite de reenvíos, código anterior invalidado, firma exitosa con metadatos, firma repetida, código incorrecto, vencido, sin emitir e intentos agotados, bloqueo, huella distinta, contrato alterado, pago revertido, proveedor caído al enviar y al sellar, roles, persistencia con SQLite y lectura del titular.
- Web, desde `web`: `npm test` (`FirmaPage.test.tsx`, `firma.service.test.ts` y el acceso desde `PagosPage.test.tsx`).

## Pendientes conocidos

- El proveedor de firma es simulado; falta integrar el proveedor real (por ejemplo, una entidad de certificación) y su sello.
- El contrato se presenta en pantalla; el PDF inmutable lo genera HU12 junto con la póliza.
- No hay pantalla para que un asesor desbloquee un proceso `BLOQUEADA`.
- `FIRMA_OTP_SECRET` no está aún en la plantilla de CloudFormation (`infra/aws`).
- La IP registrada es la que ve el backend; detrás de CloudFront o el ALB habría que leer `X-Forwarded-For` desde un proxy de confianza.

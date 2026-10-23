# Billetera digital de pólizas (HU07, BPM-31)

## Qué hace

El cliente asegurado consulta desde la app Android sus pólizas, ve el certificado digital de cada una con su código QR y lo comparte con un enlace temporal. No depende de servicios externos: el QR se genera en el dispositivo y el enlace lo sirve el mismo backend.

| Criterio de aceptación | Cómo se cumple |
|---|---|
| Lista con número, ramo, estado y fechas de inicio y vencimiento | `GET /api/v1/billetera/polizas` devuelve esos campos; la app los muestra en tarjetas |
| Certificado con número de póliza o QR | `GET .../{poliza_id}/certificado` incluye `contenido_qr`; la app dibuja el QR y el número debajo |
| Vencidas o canceladas se ven como inactivas | El backend calcula `estado` y `activa` con la fecha de Colombia; la app las agrupa en "Inactivas" con su etiqueta |
| Compartir con un mecanismo temporal | `POST .../{poliza_id}/enlaces` crea un enlace que vence (24 h por defecto) y la app abre el menú de compartir de Android |
| El cliente solo ve sus pólizas (EC08) | El backend filtra por la identidad del token; la app nunca envía el identificador del cliente |

## Endpoints

| Método y ruta | Quién | Devuelve |
|---|---|---|
| `GET /api/v1/billetera/polizas` | Cliente | Sus pólizas, vigentes primero (las que vencen antes arriba) y luego las inactivas |
| `GET /api/v1/billetera/polizas/{poliza_id}/certificado` | Cliente, solo sus pólizas | Certificado con titular, documento enmascarado, vigencia, cobertura, suma asegurada y contenido del QR |
| `POST /api/v1/billetera/polizas/{poliza_id}/enlaces` | Cliente, solo sus pólizas | `{url, expira_en}` |
| `GET /api/v1/certificados-compartidos/{token}` | Cualquiera con el enlace, mientras esté vigente | El certificado sin prima ni identificadores internos; HTML si se abre desde un navegador |

- Otros roles reciben 403. Una póliza de otro titular responde 404, igual que una que no existe, para no revelar que existe.
- Un enlace vencido responde 410 y uno inventado 404.
- Las respuestas de la billetera llevan `Cache-Control: no-store`; las del enlace también `X-Robots-Tag: noindex`.

## Estados

El backend guarda `VIGENTE` o `CANCELADA`. El vencimiento no se guarda: se calcula comparando `fecha_fin` con el día actual en Colombia (UTC−5). El último día de vigencia la póliza sigue vigente.

| Estado | `activa` | Cuándo |
|---|---|---|
| `VIGENTE` | sí | No está cancelada y hoy es `fecha_fin` o antes |
| `VENCIDA` | no | Hoy es posterior a `fecha_fin` |
| `CANCELADA` | no | Se registró la cancelación (HU18, HU22) |

## Seguridad

- **Enlaces temporales:** el token tiene 256 bits de azar. En `enlaces_certificado` solo se guarda su huella SHA-256, de modo que quien lea la base no puede armar enlaces válidos. Si la póliza cambia de titular, el enlace deja de servir.
- **Datos expuestos:** el documento del titular siempre sale enmascarado (`CC ****5678`). El certificado compartido no incluye la prima.
- **QR:** codifica `SOLVENTA|<número de póliza>|<código de verificación>`. El código se genera al emitir la póliza.
- **App:** el access token sigue sin salir del `AuthCoordinator` hacia la UI; la billetera lo pide por la interfaz `SesionAutenticada`. Si el backend lo rechaza (401), la sesión se cierra. Al cerrar sesión se borra lo cargado para que otro usuario no lo vea.
- **Auditoría:** las rutas de `/api/v1/billetera` quedan registradas como operaciones sensibles.

## Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `SOLVENTA_URL_PUBLICA` | La URL de la petición | Base de los enlaces compartidos. En AWS debe ser la URL pública del API Gateway |
| `BILLETERA_ENLACE_HORAS` | `24` | Vigencia de los enlaces, entre 1 y 168 horas |

## Datos de prueba

Mientras no exista la emisión automática (HU12), la billetera no tiene pólizas. Para un cliente ya registrado:

```powershell
cd backend
$env:CLIENTE_EMAIL="ana@gmail.com"; python sembrar_polizas.py
```

Crea cuatro pólizas: dos vigentes, una vencida y una cancelada. Es idempotente y es solo para desarrollo.

Cuando HU12 emita pólizas, debe guardarlas con `RepositorioPolizasPostgres.guardar`, incluyendo la foto del titular (nombre y documento) y un `codigo_verificacion` aleatorio.

## Pruebas

Evidencias de la prueba manual en el emulador: [evidencias/hu07](evidencias/hu07/README.md).


- Backend: `pytest tests/billetera` (dominio, repositorio, servicio y API, con cobertura del 98 al 100 % del módulo).
- Android: `./gradlew testDebugUnitTest` incluye `BilleteraCoordinatorTest`, `RemotePolizasGatewayTest`, `FormatosTest`, `CodigoQrTest`, las pruebas de las pantallas y `NavGraphBilleteraTest`, que recorre inicio → billetera → certificado → compartir.

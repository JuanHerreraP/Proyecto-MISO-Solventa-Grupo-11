# Desembolso automatizado e idempotente de indemnizaciones (HU15)

## Qué hace

Cuando un siniestro se **aprueba**, Solventa desembolsa la indemnización al cliente de inmediato y sin intervención manual:

- Si el cliente tiene una **cuenta bancaria registrada**, se le transfiere a esa cuenta.
- Si no tiene, se emite un **código de retiro** de 8 dígitos que solo el titular ve en «Mis siniestros».

La aprobación la hace un usuario de **Operaciones/Siniestros** desde la «Bandeja de siniestros» en la web. Los siniestros **paramétricos** (HU20) se aprueban y se pagan solos en el momento en que la telemetría los crea. El evaluador que queda registrado es `SISTEMA`.

## Flujo

1. El siniestro se registra en estado `REGISTRADO`, ya sea manual o paramétrico.
2. Operaciones lo aprueba o lo rechaza:
   - **Al aprobar**, el monto por defecto es `min(estimación de daños, suma asegurada)`. Operaciones puede ajustarlo, con la suma asegurada de la póliza como tope.
   - **Al rechazar**, el motivo es obligatorio y el cliente lo ve.
3. Al aprobar se crea **un único** desembolso por siniestro y se ejecuta contra la red de pagos:
   - `COMPLETADA`: el pago se hizo. Queda la referencia de la transacción (`TRF-…` para transferencias, `RET-…` para códigos de retiro).
   - `FALLIDA`: la red rechazó la operación (por ejemplo, la cuenta no existe). Operaciones puede **reintentar**. El reintento sube el número de intento y usa la cuenta vigente del cliente, de modo que si el cliente la corrige, el siguiente intento ya va a la nueva.
   - `PENDIENTE`: la red no respondió. Al reintentar se reenvía **con la misma referencia**, para que la red no pague dos veces.

## Endpoints

| Método y ruta | Quién | Devuelve |
|---|---|---|
| `GET /api/v1/desembolsos/cuenta` | Cliente | Su cuenta enmascarada, o `null` si no tiene |
| `PUT /api/v1/desembolsos/cuenta` | Cliente | Registra o reemplaza la cuenta. Cuerpo: `codigo_banco`, `tipo_cuenta` (`AHORROS`/`CORRIENTE`), `numero_cuenta` (6 a 20 dígitos) |
| `GET /api/v1/desembolsos` | Cliente | Sus desembolsos. Incluye el código de retiro |
| `GET /api/v1/operaciones/siniestros?estado=` | Operaciones/Siniestros | Bandeja de siniestros, opcionalmente filtrada por estado, con el desembolso de cada uno |
| `POST /api/v1/operaciones/siniestros/{id}/aprobacion` | Operaciones/Siniestros | Aprueba y desembolsa. Cuerpo opcional: `monto_aprobado` |
| `POST /api/v1/operaciones/siniestros/{id}/rechazo` | Operaciones/Siniestros | Rechaza. Cuerpo: `motivo` (5 a 500 caracteres) |
| `POST /api/v1/operaciones/siniestros/{id}/desembolso/reintento` | Operaciones/Siniestros | Reintenta un desembolso `FALLIDA` o `PENDIENTE` |

Bancos admitidos (`codigo_banco`):

| Código | Banco |
|---|---|
| `1007` | Bancolombia |
| `1001` | Banco de Bogotá |
| `1051` | Davivienda |
| `1013` | BBVA |
| `1023` | Occidente |
| `1052` | AV Villas |
| `1507` | Nequi |

### Códigos de error

| HTTP | Código | Cuándo |
|---|---|---|
| 401 / 403 | — | Sin sesión, o un rol distinto al del endpoint (un cliente no puede aprobar) |
| 404 | `SINIESTRO_NO_ENCONTRADO` | El siniestro no existe |
| 404 | `DESEMBOLSO_NO_ENCONTRADO` | Se pide reintentar un siniestro que no está aprobado |
| 409 | `SINIESTRO_YA_EVALUADO` | Se aprueba un siniestro rechazado (o al revés), o se aprueba otra vez con un monto distinto |
| 409 | `DESEMBOLSO_COMPLETADO` | Se reintenta un desembolso que ya se pagó |
| 422 | `MONTO_INVALIDO` | El monto supera la suma asegurada o no es positivo |

## Idempotencia

- La tabla `desembolsos` tiene un índice único por `siniestro_id`. Dos aprobaciones concurrentes no generan dos pagos: la segunda choca con la restricción y devuelve el desembolso existente.
- Aprobar de nuevo con el mismo monto devuelve el mismo resultado, sin llamar a la red. Lo mismo ocurre al rechazar dos veces.
- La referencia enviada a la red es `{desembolso_id}-{intento}`. Solo cambia cuando hay un fallo definitivo (`FALLIDA`), nunca ante un timeout.

## Seguridad

- **Tokenización:** el número de cuenta nunca se guarda. La red lo tokeniza y Solventa conserva solo el token y los últimos 4 dígitos (`Bancolombia ahorros ****1234`).
- **Código de retiro:** el cliente lo ve en su lista. La vista de Operaciones no lo expone.
- **Permisos:** las rutas de Operaciones exigen el rol `OPERACIONES_SINIESTROS`. Las del cliente exigen `CLIENTE` y filtran por la identidad del token.
- **Auditoría:** `/api/v1/desembolsos` y `/api/v1/operaciones` están en las rutas sensibles del middleware de auditoría.

## Red de pagos simulada

`RedDesembolsosSimulada` implementa el puerto `RedDesembolsos`. Se reemplaza por el adaptador real (ACH / banco) sin tocar el servicio.

| Cuenta que termina en | Resultado |
|---|---|
| `0000` | `FALLIDA` con motivo `CUENTA_INEXISTENTE` |
| `9999` | La red no responde. Queda `PENDIENTE` con motivo `RED_NO_DISPONIBLE` |
| Cualquier otra | `COMPLETADA` |

El código de retiro siempre se emite.

## Esquema de base de datos

- Columnas nuevas en `siniestros`: `monto_aprobado`, `evaluado_por`, `evaluado_en` y `motivo_rechazo`. Se agregan con la migración aditiva de `preparar_esquema_registro`.
- Tablas nuevas:
  - `desembolsos`, con FK a `siniestros` e índice único por siniestro.
  - `cuentas_desembolso`, con una por cliente que guarda solo el token y los últimos dígitos.

## Web

- **Cliente, en «Mis siniestros»:**
  - Panel «Cuenta para recibir indemnizaciones», para registrar o cambiar la cuenta.
  - En cada siniestro, la indemnización con su estado, el destino o el código de retiro, la referencia de la transacción y el motivo de rechazo si lo hubo.
- **Operaciones/Siniestros, en «Bandeja de siniestros» (`/operaciones/siniestros`):**
  - Filtros «Por evaluar», «Aprobados», «Rechazados» y «Todos».
  - «Aprobar y desembolsar», con el monto prellenado.
  - «Rechazar siniestro», con el motivo.
  - «Reintentar desembolso».

## Probar en local

1. Crea un usuario de Operaciones. El correo debe tener un dominio válido: `.local` no pasa la validación de `EmailStr`.

   ```bash
   cd backend
   ADMIN_EMAIL=operaciones@example.com ADMIN_PASSWORD='Operaciones123!' ADMIN_ROL=OPERACIONES_SINIESTROS python crear_admin.py
   ```

2. Como cliente:
   - Registra la cuenta en «Mis siniestros». Usa una terminada en `0000` para ver un fallo.
   - Reporta un siniestro sobre una póliza vigente.
3. Como Operaciones, entra a «Bandeja de siniestros» y aprueba el siniestro. Vuelve como cliente para ver el pago.
4. Para el caso paramétrico, dispara un evento de telemetría (ver [siniestros.md](siniestros.md)). El siniestro aparece ya aprobado y pagado.

## Fuera de alcance

- El onboarding no captura la cuenta bancaria. El cliente la registra después, desde «Mis siniestros».
- No existe el rol «Analista de Tesorería». La aprobación y el reintento los hace `OPERACIONES_SINIESTROS`.
- La app Android no muestra todavía los desembolsos.

## Pruebas

- Backend: `pytest tests/desembolsos`. Cubre:
  - Servicio: idempotencia, fallos, red caída y reintentos.
  - API: roles, códigos de error y ocultar el código de retiro.
  - Flujo paramétrico de punta a punta.
  - Repositorio Postgres/SQLite: restricción única, que no se guarda la cuenta completa y la migración.
- Web: `npx vitest run src/services/desembolsos.service.test.ts src/components/desembolso src/pages/BandejaSiniestrosPage.test.tsx src/pages/SiniestrosPage.test.tsx`.

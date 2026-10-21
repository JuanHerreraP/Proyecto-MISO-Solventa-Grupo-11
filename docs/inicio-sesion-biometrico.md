# Inicio de sesión biométrico (HU02, BPM-23)

## Qué hace

El cliente entra a la app Android con la huella o el rostro configurados en su dispositivo. La biometría se valida en el teléfono; Solventa nunca la recibe ni la guarda. Si la biometría no está disponible, falla o se bloquea, la app ofrece el ingreso con correo y contraseña.

## Flujo

1. **Primer ingreso con credenciales.** La app llama a `POST /api/v1/auth/login` y recibe un access token (30 minutos) y un refresh token (7 días). Luego pide el perfil con `GET /api/v1/auth/me`.
2. **Activación de la huella.** Si el dispositivo tiene biometría fuerte, la app ofrece activarla. Tras validar la huella, cifra el refresh token con una llave del Android Keystore y lo guarda cifrado.
3. **Ingresos siguientes.** El usuario valida su huella; la llave se abre durante 30 segundos. La app descifra el refresh token, llama a `POST /api/v1/auth/refresh`, recibe un par nuevo y vuelve a guardar el refresh nuevo cifrado.
4. **Cierre de sesión.** Si la huella está activada, la app solo descarta la sesión en memoria y conserva el refresh token cifrado, para volver a entrar únicamente con la huella. Si la huella no está activada, la app llama a `POST /api/v1/auth/logout`, que revoca el refresh token. Ingresar con correo y contraseña reemplaza cualquier sesión guardada.

## Endpoints nuevos del backend

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /api/v1/auth/refresh` | `{"refresh_token": "..."}` | 200 con tokens nuevos |
| `POST /api/v1/auth/logout` | `{"refresh_token": "..."}` | 204, también si la sesión ya estaba cerrada |
| `GET /api/v1/auth/me` | Cabecera `Authorization: Bearer <access>` | 200 con `id`, `nombre`, `apellido`, `email`, `rol` |

| Respuesta de error | Código | Cuándo |
|---|---|---|
| 401 | `REFRESH_EXPIRED` | El refresh token venció |
| 401 | `REFRESH_INVALID` | Firma inválida, token cerrado por logout o que no es un refresh token |
| 401 | `REFRESH_REUSED` | Se presentó un refresh token ya rotado |
| 403 | `USER_INACTIVE` | El usuario está inactivo |
| 401 | `TOKEN_REQUIRED` / `TOKEN_EXPIRED` / `TOKEN_INVALID` | `/me` sin token o con un token no válido |

## Rotación y detección de reutilización

Cada refresh token lleva un identificador (`jti`) registrado en la tabla `sesiones_refresh`. Al renovar, el token usado queda revocado con motivo `ROTACION` y apunta al nuevo. Si alguien presenta otra vez un token ya rotado, se asume que fue copiado: el backend revoca todas las sesiones del usuario y responde `REFRESH_REUSED`. Un token cerrado por logout solo responde `REFRESH_INVALID`, sin cerrar las demás sesiones.

## Comportamiento en la app

| Situación | Qué hace la app |
|---|---|
| Biometría disponible y activada | Muestra el diálogo biométrico |
| Huella no reconocida | El diálogo sigue abierto y permite otro intento |
| Demasiados intentos (bloqueo del dispositivo) | Lleva al ingreso con credenciales |
| Sin hardware, sin huellas registradas o biometría débil | Desactiva el botón y ofrece credenciales |
| Se registró una huella nueva | La llave se invalida; pide credenciales y volver a activar |
| Refresh guardado vencido o revocado | Borra la sesión guardada y pide credenciales |
| Venció el access token | Cierra la sesión en memoria; se puede volver a entrar con la huella |
| Antes de autenticar | No se compone ninguna pantalla con datos; la ventana usa `FLAG_SECURE` |

## Seguridad (EC08)

- El access token y el refresh token en claro solo viven en memoria.
- La llave AES-256-GCM no sale del Keystore, exige biometría fuerte y se invalida al registrar una huella nueva.
- La sesión biométrica se excluye de los respaldos de Android.
- `/me` solo devuelve los datos del dueño del token.

## Cómo probar en local

1. Levantar el backend: `cd backend && uvicorn app.main:app --reload --host 0.0.0.0`.
2. En el emulador, registrar una huella en Ajustes > Seguridad.
3. Correr la app; por defecto apunta a `http://10.0.2.2:8000/`. En un teléfono físico, usar `adb reverse tcp:8000 tcp:8000` y compilar con `-Psolventa.apiBaseUrl=http://localhost:8000/`.
4. Para simular la huella en el emulador: Extended controls > Fingerprint > Touch sensor.

## Pruebas

- Backend: `tests/identidad/tests_sesion` (rotación, reutilización, expiración, logout, `/me`).
- Android: `AuthCoordinatorTest` (flujo biométrico, fallback, expiración y cierre) y `MapeoBiometricoTest` (traducción de los códigos de `BiometricManager` y `BiometricPrompt`).

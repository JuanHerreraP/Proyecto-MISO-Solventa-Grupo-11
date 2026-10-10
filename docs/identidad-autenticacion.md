# Registro, onboarding seguro y autenticación basada en tokens (HU19, BPM-54)

## Qué hace

Permite registrar usuarios de Solventa, validar su identidad mediante un proveedor KYC, almacenar sus credenciales de forma segura, autenticar usuarios y emitir tokens JWT firmados para acceder a los recursos protegidos del backend.

La solución centraliza la autenticación y autorización para que los clientes web y móvil no definan permisos por su cuenta. El rol utilizado para autorizar una operación se obtiene del usuario autenticado y no de una cabecera enviada libremente por el cliente.

La integración KYC se encuentra desacoplada mediante el puerto `IdentityVerificationProvider`, permitiendo sustituir el proveedor externo sin modificar el servicio de identidad.

## Flujo

### Registro y onboarding

1. `POST /api/v1/auth/register` recibe los datos básicos del usuario.
2. Se valida que el usuario haya autorizado la validación de identidad mediante `acepta_validacion_identidad`.
3. Se verifica que no exista previamente otro usuario con el mismo correo electrónico.
4. El servicio de identidad construye una solicitud interna `VerificationRequest`.
5. El proveedor KYC configurado valida la identidad.
6. El resultado externo se traduce al modelo interno de Solventa.
7. Si la identidad es aprobada:
   - se genera el hash de la contraseña;
   - se asigna el rol `CLIENTE`;
   - se almacena el usuario;
   - se conserva la referencia entregada por el proveedor KYC;
   - se registra el evento de auditoría `USER_REGISTERED`.
8. Si la validación es rechazada, queda pendiente o el proveedor no está disponible, el registro no se completa.

### Inicio de sesión

1. `POST /api/v1/auth/login` recibe correo electrónico y contraseña.
2. Se busca el usuario registrado por correo electrónico.
3. Se valida la contraseña contra el hash almacenado.
4. Se verifica que el usuario se encuentre activo.
5. Si las credenciales son correctas se generan:
   - `access_token`;
   - `refresh_token`.
6. El evento queda registrado como `LOGIN_SUCCESS`.
7. Los intentos inválidos quedan registrados como `LOGIN_FAILED`.

### Acceso a recursos protegidos

1. El cliente envía el Access Token en la cabecera:

```http
Authorization: Bearer <access_token>
```

2. `get_current_user` valida:
   - existencia del token;
   - firma RSA;
   - expiración;
   - tipo de token;
   - usuario asociado;
   - estado activo del usuario.
3. Para operaciones restringidas, `requiere_roles(...)` verifica que el usuario tenga uno de los roles autorizados.
4. Los accesos rechazados quedan registrados en auditoría.

## API

| Endpoint | Uso | Autenticación |
| --- | --- | --- |
| `POST /api/v1/auth/register` | Registro y onboarding del usuario | No |
| `POST /api/v1/auth/login` | Inicio de sesión y generación de tokens | No |
| `GET /api/v1/auth/users` | Lista de usuarios registrados | Actualmente no protegida |

### Registro

`POST /api/v1/auth/register`

Ejemplo de solicitud:

```json
{
  "nombre": "Maria",
  "apellido": "Torres",
  "email": "maria.torres@correo.com",
  "password": "Password123!",
  "tipo_documento": "CC",
  "numero_documento": "123456789",
  "fecha_nacimiento": "1995-06-15",
  "acepta_validacion_identidad": true
}
```

Ejemplo de respuesta exitosa:

```json
{
  "id": "84bddffc-1478-47ef-95ab-f89230a7380f",
  "nombre": "Maria",
  "apellido": "Torres",
  "email": "maria.torres@correo.com",
  "rol": "CLIENTE",
  "kyc_validado": true,
  "fecha_creacion": "2026-10-08T20:30:00Z"
}
```

| Respuesta | Cuándo |
| --- | --- |
| `201` | Usuario registrado y KYC aprobado |
| `202` | La validación KYC requiere revisión adicional |
| `409` | Ya existe un usuario con el correo electrónico |
| `422` | No se autorizó la validación de identidad o el KYC fue rechazado |
| `503` | El proveedor KYC no se encuentra disponible |

La contraseña nunca se devuelve en la respuesta del registro.

### Login

`POST /api/v1/auth/login`

Solicitud:

```json
{
  "email": "maria.torres@correo.com",
  "password": "Password123!"
}
```

Respuesta:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_expires_in": 604800
}
```

| Respuesta | Cuándo |
| --- | --- |
| `200` | Credenciales correctas y usuario activo |
| `401` | Correo o contraseña incorrectos |
| `403` | El usuario existe pero está inactivo |

Por seguridad, cuando el correo no existe o la contraseña es incorrecta se devuelve el mismo mensaje:

`El correo electrónico o la contraseña son incorrectos.`

Esto evita revelar si una cuenta determinada existe en Solventa.

## Contraseñas

Las contraseñas no se almacenan en texto plano.

El backend utiliza `pwdlib` mediante `PasswordHash.recommended()` para generar y verificar el hash de la contraseña.

El modelo persistente almacena únicamente:

```text
password_hash
```

Los endpoints públicos nunca devuelven este valor.

## Tokens JWT

La autenticación utiliza JWT firmados mediante `RS256`.

Se utilizan dos tipos de token:

| Token | Vigencia por defecto | Uso |
| --- | --- | --- |
| Access Token | 30 minutos | Autorizar peticiones a recursos protegidos |
| Refresh Token | 7 días | Renovar una sesión sin solicitar nuevamente las credenciales |

Los valores pueden modificarse mediante variables de entorno.

### Claims

El Access Token contiene:

```json
{
  "sub": "<usuario_id>",
  "email": "maria.torres@correo.com",
  "rol": "CLIENTE",
  "iat": "<fecha_emision>",
  "exp": "<fecha_expiracion>",
  "type": "access"
}
```

El Refresh Token utiliza la misma información, pero identifica:

```json
{
  "type": "refresh"
}
```

La firma se genera utilizando la llave privada y se verifica utilizando la llave pública.

## Validación del Access Token

`validar_access_token` verifica:

- firma RS256;
- fecha de expiración;
- que `type` sea `access`;
- existencia del claim `sub`.

Si la validación criptográfica o estructural falla, el token no puede utilizarse para acceder a los endpoints protegidos.

La dependencia `get_current_user` agrega además la validación contra persistencia:

- el usuario asociado al `sub` debe existir;
- el usuario debe permanecer activo.

| Código interno | HTTP | Situación |
| --- | --- | --- |
| `TOKEN_REQUIRED` | `401` | No se envió token |
| `TOKEN_EXPIRED` | `401` | El Access Token expiró |
| `TOKEN_INVALID` | `401` | Firma, estructura o tipo de token inválidos |
| `USER_NOT_FOUND` | `401` | El usuario contenido en el token ya no existe |
| `USER_INACTIVE` | `403` | El usuario se encuentra inactivo |
| `ACCESS_DENIED` | `403` | El usuario no tiene el rol requerido |
| `ROLE_INVALID` | `403` | El rol almacenado no corresponde a un rol reconocido |

## Roles y autorización

Los roles definidos actualmente son:

| Rol |
| --- |
| `CLIENTE` |
| `ASESOR_VENTAS` |
| `ANALISTA_RIESGOS` |
| `OPERACIONES_SINIESTROS` |
| `SOCIO_DISTRIBUCION` |
| `INGENIERO_INTEGRACIONES` |
| `SERVICIO_INTERNO` |

Los usuarios creados mediante el registro público reciben inicialmente el rol:

```text
CLIENTE
```

La autorización se realiza en el backend mediante las dependencias:

```python
get_current_user
rol_actual
requiere_roles(...)
```

`rol_actual` obtiene el rol desde el usuario autenticado.

Esto reemplaza el mecanismo provisional en el que algunos componentes recibían el rol mediante la cabecera `X-Rol`.

Para pruebas aisladas de módulos anteriores pueden utilizarse `dependency_overrides`, pero en ejecución real los permisos deben derivarse del usuario autenticado mediante JWT.

## Integración KYC y EC06

El servicio de identidad depende del puerto:

```text
IdentityVerificationProvider
```

Actualmente existen tres adaptadores:

| Proveedor | Adaptador | Puerto local |
| --- | --- | --- |
| A | `KYCProviderAAdapter` | `8001` |
| B | `KYCProviderBAdapter` | `8002` |
| C | `KYCProviderCAdapter` | `8003` |

El proveedor activo se selecciona mediante:

```text
KYC_PROVIDER
```

Valores soportados:

```text
A
B
C
```

Por defecto se utiliza:

```text
A
```

El servicio de registro no conoce los detalles HTTP específicos del proveedor. Solo depende de `IdentityVerificationProvider`.

Cada adaptador traduce el contrato externo al modelo interno:

```text
VerificationResult
```

con:

- `verification_id`;
- `status`;
- `risk_score`;
- `provider_name`;
- `checked_at`.

Los estados internos son:

| Estado interno | Significado |
| --- | --- |
| `APPROVED` | Identidad aprobada |
| `REJECTED` | Identidad rechazada |
| `IN_REVIEW` | Requiere revisión adicional |

Esta separación permite sustituir A, B o C sin modificar `ServicioIdentidad`, cumpliendo el escenario arquitectónico EC06.

## Persistencia

El módulo de identidad define las tablas:

### `usuarios`

Contiene:

- identificador UUID;
- nombre;
- apellido;
- correo electrónico;
- hash de contraseña;
- rol;
- estado activo;
- tipo de documento;
- número de documento;
- fecha de nacimiento;
- resultado de validación KYC;
- referencia del proveedor KYC;
- consentimiento KYC;
- fecha de creación.

### `eventos_autenticacion`

Almacena la trazabilidad de eventos de autenticación y autorización.

Puede registrar:

- usuario;
- correo electrónico;
- tipo de evento;
- resultado exitoso o fallido;
- detalle;
- dirección IP;
- User-Agent;
- fecha.

La auditoría utiliza una sesión de base de datos independiente. Un error escribiendo la auditoría no debe interrumpir el proceso principal de registro, login o autorización.

## Auditoría

Actualmente se encuentran definidos los siguientes eventos:

| Evento | Uso |
| --- | --- |
| `USER_REGISTERED` | Registro completado correctamente |
| `REGISTRATION_REJECTED` | Registro rechazado |
| `LOGIN_SUCCESS` | Inicio de sesión correcto |
| `LOGIN_FAILED` | Inicio de sesión fallido |
| `TOKEN_REQUIRED` | Acceso sin token |
| `TOKEN_INVALID` | Token inválido |
| `TOKEN_EXPIRED` | Token expirado |
| `TOKEN_REFRESHED` | Renovación del token |
| `ACCESS_DENIED` | Usuario o rol sin autorización |

La auditoría no debe almacenar:

- contraseña;
- hash de contraseña;
- Access Token;
- Refresh Token;
- llave privada de firma.

## Configuración

| Variable | Uso | Por defecto |
| --- | --- | --- |
| `DATABASE_URL` | Conexión a la base de datos | `sqlite:///./solventa.db` |
| `KYC_PROVIDER` | Proveedor KYC activo | `A` |
| `KYC_PROVIDER_A_URL` | URL del proveedor A | `http://127.0.0.1:8001` |
| `KYC_PROVIDER_B_URL` | URL del proveedor B | `http://127.0.0.1:8002` |
| `KYC_PROVIDER_C_URL` | URL del proveedor C | `http://127.0.0.1:8003` |
| `JWT_PRIVATE_KEY_PATH` | Llave privada para firmar JWT | `keys/private_key.pem` |
| `JWT_PUBLIC_KEY_PATH` | Llave pública para validar JWT | `keys/public_key.pem` |
| `JWT_ACCESS_TOKEN_MINUTES` | Vigencia del Access Token | `30` |
| `JWT_REFRESH_TOKEN_DAYS` | Vigencia del Refresh Token | `7` |

En ambientes desplegados, `DATABASE_URL` debe apuntar a PostgreSQL y las llaves privadas deben administrarse mediante mecanismos seguros de secretos del ambiente.

## Pruebas

Las pruebas relacionadas con HU19 se encuentran principalmente en:

```text
backend/tests/identidad/tests_auth/
```

La suite cubre:

- modelos de registro y autenticación;
- registro correcto;
- consentimiento obligatorio;
- usuario duplicado;
- KYC aprobado;
- KYC rechazado;
- KYC en revisión;
- hash de contraseña;
- login correcto;
- contraseña incorrecta;
- usuario inexistente;
- usuario inactivo;
- generación de Access Token;
- generación de Refresh Token;
- firma RS256;
- expiración;
- token inválido;
- token faltante;
- usuario inexistente asociado al token;
- usuario inactivo;
- resolución de roles;
- acceso permitido;
- acceso rechazado;
- auditoría de eventos.

Las pruebas de regresión KYC se encuentran en:

```text
backend/tests/identidad/tests_KYC_EC06/
```

y se ejecutan para los proveedores A, B y C.

Para ejecutar todas las pruebas del backend:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

Para ejecutar únicamente autenticación:

```bash
python -m pytest tests/identidad/tests_auth -v
```

Para ejecutar únicamente la regresión KYC:

```bash
python -m pytest tests/identidad/tests_KYC_EC06 -v
```

## Pendientes conocidos

- **Refresh Token:** actualmente se genera y se puede validar internamente, pero todavía no existe un endpoint `POST /api/v1/auth/refresh` que permita renovar el Access Token desde el cliente.
- **Almacenamiento seguro en web:** el frontend deberá definir el manejo seguro de sesión. El Refresh Token no debe almacenarse de forma permanente en `localStorage`; se debe implementar una estrategia acorde con los criterios de seguridad definidos para HU19.
- **Llaves JWT:** la llave privada no debe almacenarse en el repositorio. En AWS deberá administrarse mediante un mecanismo seguro de secretos.
- **Endpoint de usuarios:** `GET /api/v1/auth/users` actualmente no tiene una dependencia de autenticación o autorización asociada y debe protegerse antes de considerarlo un endpoint administrativo definitivo.
- **Base de datos local:** cuando `DATABASE_URL` no está definida se utiliza SQLite para facilitar la ejecución local. El ambiente desplegado utilizará PostgreSQL.
- **Migraciones:** las tablas se crean actualmente mediante `Base.metadata.create_all`; la evolución del esquema deberá gestionarse mediante migraciones cuando el modelo se estabilice.
- **KYC real:** los proveedores A, B y C actuales son simuladores utilizados para validar el desacoplamiento EC06. Los contratos deberán adaptarse cuando exista un proveedor real.
- **Manejo de sesión:** el Access Token tiene expiración de 30 minutos, pero una política completa de expiración por inactividad requiere integrar el mecanismo de renovación y manejo de sesión del cliente.
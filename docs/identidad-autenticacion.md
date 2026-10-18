# Identidad, autenticación, sesiones y control de acceso (HU19, EC08, EC06)

## Qué hace

Permite registrar usuarios de Solventa, validar su identidad mediante un proveedor KYC, almacenar sus credenciales de forma segura, autenticar usuarios y emitir tokens JWT firmados para acceder a los recursos protegidos del backend.

La solución centraliza la autenticación y autorización para que los clientes web y móvil no definan permisos por su cuenta. El rol utilizado para autorizar una operación se obtiene del usuario autenticado y no de una cabecera enviada libremente por el cliente.

La integración KYC se encuentra desacoplada mediante el puerto `IdentityVerificationProvider`, permitiendo sustituir el proveedor externo sin modificar el servicio de identidad.

Permite al manager de la aplicación, identificado por `SERVICIO_INTERNO`, crear y
listar usuarios de Solventa. El alta administrativa asigna cualquiera de los roles
definidos; no crea nuevas definiciones de roles ni habilita su selección pública.

El registro público continúa asignando `CLIENTE`. Crear una cuenta con rol
`SOCIO_DISTRIBUCION` no crea ni vincula automáticamente una organización: ese
proceso corresponde al [alta de socios](socios-distribucion.md).

Este documento reúne los contratos de identidad, sesión nativa y web, administración de usuarios y control de acceso y auditoría (HU19, EC08), con KYC desacoplado (EC06) y renovación usada por la biometría Android (HU02).

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

### Sesión web

1. Al abrir la aplicación, intenta restaurar la sesión mediante la cookie y espera
   el resultado antes de montar las pantallas.
2. Para iniciar sesión, obtiene el reto CSRF y envía correo y contraseña al login web.
3. El backend establece las cookies y devuelve el access token; React consulta
   `/api/v1/auth/me` y muestra las rutas permitidas para el rol.
4. Antes de que venza el access token, solicita una renovación. El backend rota
   el refresh y actualiza la cookie.
5. Tras 30 minutos sin actividad, la sesión deja de ser válida y vuelve al login.
6. Al cerrar sesión, el backend revoca la sesión y elimina ambas cookies.

### Alta administrativa de usuarios

1. Un operador autorizado aprovisiona el primer manager en la base de datos; la
   API administrativa requiere un manager existente.
2. El manager inicia sesión y obtiene un access token. En web se utiliza el
   [flujo de cookies y CSRF](identidad-autenticacion.md#sesión-web-y-seguridad); para Swagger o un cliente nativo puede
   usar `POST /api/v1/auth/login`.
3. Envía `Authorization: Bearer <access_token>` al listar o crear usuarios.
4. El backend valida la identidad y comprueba el rol `SERVICIO_INTERNO` vigente.
5. Al crear, valida consentimiento, datos y unicidad de correo/documento, consulta
   KYC, genera el hash de contraseña y guarda el rol solicitado.
6. Devuelve los datos públicos del usuario y registra quién lo creó y qué rol asignó.
   Los accesos rechazados y el listado también quedan auditados.
7. El usuario creado inicia sesión con sus credenciales y consulta `/me` para
   obtener su identidad y rol.

### Control de acceso y auditoría (HU19, EC08)

1. El cliente envía el access token en `Authorization: Bearer <access_token>`.
2. El backend valida firma, expiración, usuario activo y vigencia de su sesión.
3. Consulta el rol actual en persistencia y verifica los roles permitidos.
4. Si opera un cliente, comprueba que la oferta o el consentimiento le pertenezcan.
5. Rechaza una identidad inválida con 401 o permisos insuficientes con 403, antes
   de consultar o modificar el recurso.
6. Registra el resultado y los datos de auditoría sin incluir tokens ni contraseñas.
7. En web, la ruta consulta `/me` antes de montar la pantalla; ocultar opciones no
   sustituye la validación de la API.

## Endpoints

| Método y ruta | Uso | Autenticación |
| --- | --- | --- |
| `POST /api/v1/auth/register` | Registro y onboarding del usuario | No |
| `POST /api/v1/auth/login` | Inicio de sesión y generación de tokens | No |
| `GET /api/v1/auth/users` | Lista de usuarios registrados | Solo `SERVICIO_INTERNO` |
| `POST /api/v1/auth/users` | Crea usuarios con un rol definido | Solo `SERVICIO_INTERNO` |
| `POST /api/v1/auth/refresh` | Rota el refresh y devuelve un nuevo par de tokens | Refresh firmado y sesión válida en JSON |
| `POST /api/v1/auth/logout` | Revoca la sesión; responde 204 | Refresh firmado en JSON |
| `GET /api/v1/auth/me` | Devuelve `id`, `nombre`, `apellido`, `email` y `rol` propios | JWT Bearer y usuario activo |
| `GET /api/v1/auth/web/csrf` | Devuelve `csrf_token` y establece o recupera su cookie | Sin Bearer; valida Origin si se envía |
| `POST /api/v1/auth/web/login` | Inicia sesión y establece cookies | Credenciales, Origin autorizado y CSRF |
| `POST /api/v1/auth/web/refresh` | Rota el refresh de la cookie | Cookie de sesión, Origin autorizado y CSRF |
| `POST /api/v1/auth/web/logout` | Revoca la sesión y elimina cookies; responde 204 | Origin autorizado y CSRF; cookie si existe |

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
  "celular": "3001234567",
  "selfie_base64": "<JPEG codificado en Base64>",
  "acepta_validacion_identidad": true
}
```

`celular` y `selfie_base64` son opcionales para mantener la compatibilidad con clientes existentes; la app Android recopila ambos y envía la selfie como JPEG codificado en Base64. El proveedor KYC de demostración no analiza la imagen ni ejecuta una prueba de vida: su resultado es determinista según el documento y no sirve para verificar identidades reales.

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
| `409` | Ya existe un usuario con el correo electrónico o documento |
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

### Renovación y cierre nativos

`POST /api/v1/auth/refresh` y `POST /api/v1/auth/logout` reciben:

```json
{
  "refresh_token": "<jwt>"
}
```

Refresh devuelve el mismo contrato JSON que login, con un nuevo access token y un nuevo refresh token. El anterior se revoca por rotación; su reutilización se rechaza con `401 REFRESH_REUSED`. Los tokens expirados o inválidos responden `401 REFRESH_EXPIRED` o `401 REFRESH_INVALID`; un usuario inactivo responde `403 USER_INACTIVE`.

Logout responde `204` aunque la sesión ya esté cerrada; un token inválido responde `401 REFRESH_INVALID`. Estos endpoints no establecen cookies y mantienen el contrato nativo de Android. El navegador utiliza los endpoints `/api/v1/auth/web`.

### Perfil del usuario autenticado

`GET /api/v1/auth/me` requiere Bearer y devuelve exclusivamente `id`, `nombre`, `apellido`, `email` y `rol` del usuario autenticado. Sin identidad válida responde 401; un usuario inactivo recibe 403.

### Administración de usuarios (EC08)

| Método y ruta | Quién | Entrada | Respuesta |
| --- | --- | --- | --- |
| `GET /api/v1/auth/users` | `SERVICIO_INTERNO` | JWT Bearer | 200 con usuarios registrados |
| `POST /api/v1/auth/users` | `SERVICIO_INTERNO` | JWT Bearer y datos de registro más `rol` | 201 con los datos públicos del usuario |
| `GET /api/v1/auth/me` | Usuario autenticado | JWT Bearer | 200 con `id`, nombre, apellido, email y rol propios |

#### Ejemplo de creación

`POST /api/v1/auth/users` con `Authorization: Bearer <access_token>`:

```json
{
  "nombre": "Ana",
  "apellido": "Perez",
  "email": "integraciones@example.com",
  "password": "CambiarEstaClave123!",
  "tipo_documento": "CC",
  "numero_documento": "1000000001",
  "fecha_nacimiento": "1990-01-01",
  "acepta_validacion_identidad": true,
  "rol": "INGENIERO_INTEGRACIONES"
}
```

La respuesta de creación contiene `id`, `nombre`, `apellido`, `email`, `rol`,
`kyc_validado` y `fecha_creacion`. Nunca devuelve la contraseña ni su hash.

#### Errores

| HTTP | Cuándo |
| --- | --- |
| 401 | Falta un token válido o la sesión expiró/fue revocada |
| 403 | El usuario está inactivo o no tiene el rol requerido |
| 409 | Correo o documento duplicado |
| 422 | Rol desconocido, datos inválidos, falta de consentimiento o KYC rechazado |
| 202 | KYC requiere revisión; no se crea la cuenta |
| 503 | Proveedor KYC no disponible |

### Contrato de sesión web

| Endpoint | Uso |
| --- | --- |
| `GET /api/v1/auth/web/csrf` | Establece o recupera el reto CSRF, sin prolongar la sesión |
| `POST /api/v1/auth/web/login` | Recibe email y password; establece las cookies |
| `POST /api/v1/auth/web/refresh` | Lee y rota el refresh desde la cookie; no recibe tokens en el cuerpo |
| `POST /api/v1/auth/web/logout` | Revoca la sesión y elimina ambas cookies |

Login y refresh devuelven solo `access_token`, `token_type`, `expires_in` y
`csrf_token`. Las respuestas web incluyen `Cache-Control: no-store`.

Antes de cada POST, React obtiene el reto y lo envía en `X-CSRF-Token`. El backend
comprueba que coincida con la cookie y que `Origin` pertenezca a la lista explícita
de orígenes autorizados. Los tres POST rechazan la falta de Origin o CSRF con 403,
sin alterar la sesión existente. Un refresh inválido devuelve 401 y elimina las
cookies. Las peticiones de sesión usan `credentials: include`; las APIs con Bearer
usan `credentials: omit` y siguen validando permisos en el backend.

Los endpoints nativos `/api/v1/auth/login`, `/refresh` y `/logout` mantienen su
contrato JSON para Android: no establecen cookies y requieren el refresh explícito.
El navegador usa exclusivamente los endpoints `/web`.

### Matriz de permisos

Este módulo aplica controles a endpoints existentes. No expone un endpoint propio
para consultar auditoría; los eventos se almacenan en la base de datos.

| Método y ruta | Roles permitidos |
| --- | --- |
| `GET`, `POST /api/v1/auth/users` | `SERVICIO_INTERNO` |
| `POST /api/v1/socios`, `GET`, `PATCH /api/v1/socios/{socio_id}` | `SERVICIO_INTERNO`, `INGENIERO_INTEGRACIONES` |
| `POST /api/v1/socios/{socio_id}/credenciales` | `SERVICIO_INTERNO`, `INGENIERO_INTEGRACIONES` |
| `POST /identidad/verificaciones` | `SERVICIO_INTERNO` |
| `POST /api/v1/perfiles-riesgo`, `POST /api/v1/enriquecimientos` | `SERVICIO_INTERNO`, `ASESOR_VENTAS` |
| `GET /api/v1/perfiles-riesgo/{cliente_id}`, `GET /api/v1/enriquecimientos/{cliente_id}` | `SERVICIO_INTERNO`, `ANALISTA_RIESGOS` |
| `GET /api/v1/perfiles-riesgo/{cliente_id}/oferta` | `SERVICIO_INTERNO`, `ASESOR_VENTAS`, `ANALISTA_RIESGOS`; `CLIENTE` solo su propia oferta |
| `POST /api/v1/consentimientos` | `SERVICIO_INTERNO`, `ASESOR_VENTAS`; `CLIENTE` solo para sí mismo |
| `GET /api/v1/auth/me` | Usuario con sesión válida; devuelve solo sus propios datos |
| `POST /api/v1/autorizaciones/socios` | Token de integración, tenant, estado y scope válidos |

El identificador propio del cliente corresponde al `id` del usuario autenticado,
que también se devuelve en `/auth/me`. Las APIs de perfiles y consentimientos deben
usar ese valor como `cliente_id`. El control se realiza antes de consultar o
modificar el recurso. Los roles internos conservan acceso transversal conforme a
la matriz; todavía no existe un modelo de asignación de clientes a asesores.

Registro y login permanecen públicos. Refresh y logout requieren el refresh token
firmado y su sesión; OAuth de socios requiere sus credenciales de integración.
Salud y documentación de API permanecen públicas. El registro público sigue
invocando KYC internamente sin conceder acceso al endpoint KYC directo.

Las APIs de integración de socios mantienen sus tokens específicos, validación de
tenant, estado y scopes. Un token de usuario no sustituye un token de integración.

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

Los access tokens de sesión incluyen `sid`, y los refresh incluyen un `jti` único para rotación y revocación. El rol para autorizar se consulta en persistencia, aunque el JWT contenga el claim `rol`.

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

Cuando el token contiene `sid`, también se valida la vigencia de la sesión, su revocación y el límite de inactividad. Una sesión expirada o revocada responde 401.

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

Roles admitidos: `CLIENTE`, `ASESOR_VENTAS`, `ANALISTA_RIESGOS`,
`OPERACIONES_SINIESTROS`, `SOCIO_DISTRIBUCION`, `INGENIERO_INTEGRACIONES`
y `SERVICIO_INTERNO`.

Un `INGENIERO_INTEGRACIONES` puede administrar socios, pero no crear o listar
usuarios mediante estos endpoints. El manager sí puede crear nuevas cuentas
`SERVICIO_INTERNO`. El backend obtiene los permisos del usuario autenticado; una
cabecera `X-Rol` o un campo enviado al registro público no eleva privilegios.

La matriz de permisos se encuentra en la sección Endpoints de este documento.

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

### `sesiones_refresh`

Conserva el `jti`, usuario, expiración, revocación, motivo, sesión de reemplazo y `ultima_actividad` para rotar refresh, detectar reutilización y controlar inactividad.

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
| `REFRESH_FAILED` | Renovación fallida |
| `REFRESH_REUSE_DETECTED` | Reutilización de un refresh rotado |
| `LOGOUT` | Cierre de sesión |
| `SENSITIVE_OPERATION` | Operación sensible sin evento específico |
| `ACCESS_DENIED` | Usuario o rol sin autorización |

La auditoría no debe almacenar:

- contraseña;
- hash de contraseña;
- Access Token;
- Refresh Token;
- llave privada de firma.

Los rechazos devuelven 401 si falta una identidad válida y 403 si la identidad no
tiene permiso. Las respuestas 401 incluyen `WWW-Authenticate`.

Las dependencias registran los eventos específicos de autenticación y rol. El
middleware registra como `ACCESS_DENIED` cualquier 401/403 que no haya sido
registrado previamente, incluidos rechazos por propiedad, OAuth y scopes.

Las operaciones sensibles se registran con su resultado como `SENSITIVE_OPERATION` si no
cuentan ya con un evento específico: escrituras, listado de usuarios, consultas
de socios, perfiles y enriquecimientos. Las operaciones de socios mantienen además
su auditoría de dominio. Se conserva actor, fecha, método, recurso, resultado, IP
y user agent. Para integraciones se incluye socio y tenant. No se guardan tokens,
contraseñas, secretos, cuerpos de petición ni parámetros de consulta.

Los eventos se persisten en `eventos_autenticacion`, usando una sesión de base de
datos independiente. Los fallos al escribir auditoría se registran en el logger y
no interrumpen la operación, según la política existente del proyecto.

## Sesión web y seguridad

La web conserva el access token únicamente en memoria y envía
`Authorization: Bearer <access_token>` a los recursos protegidos. El refresh token
se guarda únicamente en una cookie del backend: no se devuelve en el JSON web ni
se guarda en localStorage o sessionStorage.

La cookie utiliza `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` y no tiene Domain.
Con Secure habilitado se llama `__Host-solventa_refresh`; el prefijo impide cookies
con Domain o con un Path diferente. Una segunda cookie HttpOnly almacena el reto
CSRF. El backend emite y elimina las cookies; React no puede leerlas.

### Restauración, renovación y cierre

Al recargar la página, la aplicación espera la restauración desde la cookie antes
de montar las páginas. Si la cookie no existe, las páginas públicas siguen
accesibles. Si la sesión continúa vigente, obtiene un nuevo access token.

La renovación se hace cuando queda un minuto de vigencia o la API devuelve
`TOKEN_EXPIRED`/`SESSION_EXPIRED`; se reintenta una sola vez. Las peticiones de una
pestaña comparten la renovación. Web Locks serializa la rotación entre pestañas
cuando el navegador lo admite. BroadcastChannel comparte actividad y cierre de
sesión entre pestañas, sin intercambiar tokens.

Home incluye “Cerrar sesión”. Tras un logout confirmado por el servidor se limpian
el token en memoria y las cookies. Si falla la petición, se muestra un error para
permitir reintentar, sin anunciar un cierre que no se pudo confirmar.

### Inactividad

El access token sigue vigente durante 30 minutos desde la emisión. La sesión
expira tras 30 minutos de inactividad aunque la cookie dure hasta siete días.

La web registra teclado, pulsaciones, desplazamiento y toque. Cada 15 segundos
comprueba el plazo y sincroniza con `/auth/me` solo si hubo interacción. Los retos
CSRF, temporizadores y respuestas de renovación no cuentan como interacción del
usuario. La web comprueba nuevamente el plazo al interactuar o enviar peticiones,
para cubrir temporizadores suspendidos en segundo plano.

El backend conserva `ultima_actividad` en `sesiones_refresh`. Las peticiones
autenticadas actualizan ese valor. Al cumplir 30 minutos, revoca por `INACTIVIDAD`
y rechaza tanto acceso como renovación; una recarga no evita este control. El
backend mide actividad por peticiones, sin asumir que prueben presencia física.

Los access tokens nuevos incluyen `sid`. Logout y revocación bloquean los tokens
de esa sesión. Los tokens antiguos sin `sid` conservan su expiración JWT.

## Rutas y navegación web

`RutaProtegida` comprueba la sesión mediante `/api/v1/auth/me` antes de montar la
pantalla. Mientras consulta, muestra “Verificando acceso…”. No confía en un rol
almacenado en el navegador ni en el contenido del JWT sin consultar el backend.

- `/home` requiere una sesión válida y conserva Home para todos los roles.
- `/admin/socios/nuevo` requiere `INGENIERO_INTEGRACIONES` o `SERVICIO_INTERNO`,
  incluso al escribir la URL, recargar o navegar con atrás/adelante.
- Sin sesión, las rutas protegidas redirigen al login.
- Con sesión pero sin el rol requerido, vuelven a Home con un aviso de acceso
  denegado; el formulario restringido no llega a montarse.
- `/login` y `/registro` permanecen públicos.

La lista de roles de socios se comparte entre el botón de Home y la ruta. Cada
cambio de destino comprueba nuevamente los permisos; logout y expiración vuelven
al login. El backend sigue validando todas las operaciones independientemente de
la navegación web.

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

### Cookies y CORS web

| Variable backend | Valor predeterminado |
| --- | --- |
| `WEB_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` |
| `WEB_COOKIE_SECURE` | `true` |
| `WEB_COOKIE_SAMESITE` | `lax` |
| `APP_ENV` | `development` |

CORS permite credenciales y solo orígenes explícitos, sin comodines. Configurar
`APP_ENV=production` impide desactivar Secure. `SameSite=None` también exige Secure.
En producción se requiere HTTPS. Si web y API están en sitios diferentes, puede
ser necesario SameSite=None; las restricciones de cookies de terceros del navegador
pueden impedir ese despliegue. Se prefiere servirlos bajo el mismo sitio.

Para HTTP local, desde `backend`:

```bash
WEB_COOKIE_SECURE=false WEB_ALLOWED_ORIGINS=http://localhost:5173 .venv/bin/uvicorn app.main:app --reload
```

Usar `http://localhost:5173` para la web y `VITE_API_URL=http://localhost:8000`.
Mantener el mismo hostname (no mezclar localhost con 127.0.0.1). La excepción local
usa cookies sin el prefijo `__Host-`; no debe utilizarse en producción.
Las variables deben exportarse o pasarse al proceso: el backend no carga un .env
automáticamente. Reiniciar el backend tras cambiar la configuración.

## Cómo probar en local

1. Iniciar backend y proveedor KYC según el [README principal](../README.md).
2. Disponer de una cuenta manager aprovisionada por un operador autorizado.
3. Abrir `/docs`, iniciar sesión en `/api/v1/auth/login` y copiar `access_token`.
4. En **Authorize**, pegar el access token y ejecutar el listado y la creación.
5. Repetir con otro rol para comprobar el rechazo 403; sin token debe responder 401.

### Permisos y auditoría

1. Iniciar la API y autenticar una cuenta de cada rol mediante los contratos de
   [identidad](identidad-autenticacion.md) o [sesión web](identidad-autenticacion.md#sesión-web-y-seguridad).
2. Consultar `/api/v1/auth/me` para comprobar el `id` y el rol efectivos.
3. Ejecutar las operaciones de la matriz con Bearer y verificar 200/201, 401 o 403.
4. Como cliente, cambiar el `cliente_id` de oferta o consentimiento y comprobar 403.
5. Revisar los registros de `eventos_autenticacion` en la base de datos del ambiente.

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

### Sesiones nativas y web

Backend: atributos y eliminación de cookies, ausencia de refresh en JSON, rotación,
restauración, límite de inactividad, CSRF y origen inválidos, CORS explícito y
compatibilidad del contrato Android. Web: reto CSRF, envío de credenciales,
restauración antes del montaje, renovación concurrente, expiración y logout.


Desde `backend`:

```bash
.venv/bin/python -m pytest tests/identidad/tests_sesion/test_api_sesion_web.py tests/identidad/tests_sesion/test_api_sesion.py
```

Desde `web`:

```bash
npm test -- --run src/services/session.test.ts src/App.test.tsx
```

### Administración de usuarios

Desde `backend`:

```bash
.venv/bin/python -m pytest tests/identidad/tests_sesion/test_api_usuarios_admin.py tests/identidad/tests_sesion/test_api_control_acceso.py
```

Cubren creación de todos los roles, duplicados, rol desconocido, registro público
sin escalamiento, accesos permitidos/denegados y persistencia de auditoría.

### Control de acceso y navegación

La suite `tests/identidad/tests_sesion/test_api_control_acceso.py` utiliza JWT reales
y una base de datos aislada para comprobar la matriz de roles, pertenencia de
recursos, ausencia de token, suplantación de rol por cabecera, rechazo por scope y
persistencia de los eventos sin duplicación. Las pruebas del experimento KYC
sobrescriben únicamente la identidad para aislar su contrato de proveedor.


Desde `backend`:

```bash
.venv/bin/python -m pytest tests/identidad/tests_sesion/test_api_control_acceso.py tests/socios/test_api_autorizacion.py
```

Desde `web`:

```bash
npm test -- --run src/App.test.tsx src/pages/HomePage.test.tsx
```
# Administración e integración de socios de distribución

Este documento describe el recorrido completo definido en HU24 (BPM-76) y
EC13 (BPM-87) para incorporar un socio de distribución, como un banco, una
aerolínea o un comercio electrónico. El flujo permite registrar su configuración
técnica, asignarle un espacio lógico, generar sus credenciales e identificarlo
cuando consume las APIs de Solventa.

La incorporación utiliza contratos y credenciales estándar. Por esta razón, dar
de alta un nuevo socio no requiere modificar los servicios de cotización,
emisión ni el núcleo de negocio.

## Recorrido general

1. Un Ingeniero de Integraciones registra la ficha técnica del socio.
2. Solventa crea un `socio_id` y aprovisiona un `tenant_id` lógico.
3. El ingeniero genera las credenciales técnicas del socio.
4. Solventa entrega un `client_id` y un `client_secret`; el secreto solo se
   muestra en la respuesta de creación.
5. El sistema del socio intercambia esas credenciales por un token OAuth.
6. El token identifica al socio, su tenant y los scopes autorizados.
7. Antes de permitir una operación, Solventa valida el token y contrasta sus
   permisos con la configuración vigente del socio.

## Acceso administrativo y roles

Los endpoints de administración requieren un JWT de usuario válido y uno de
estos roles:

- `INGENIERO_INTEGRACIONES`: administra la configuración técnica de socios.
- `SERVICIO_INTERNO`: permite ejecutar el proceso desde servicios internos
  autorizados.

La validación reutiliza la dependencia `requiere_roles` del módulo de identidad.
Un usuario autenticado que no tenga uno de estos roles recibe `403 Forbidden`.

El JWT administrativo y el token técnico del socio cumplen propósitos
diferentes. El primero identifica a una persona que administra la plataforma;
el segundo identifica al sistema de un socio que consume las APIs.

## Alta y configuración del socio

Durante el alta, la API valida los datos obligatorios y que no exista otro
registro con el mismo NIT. Después genera los identificadores, guarda la
configuración en PostgreSQL y registra una auditoría de tipo `ALTA`.

El `tenant_id` no representa una base de datos ni un esquema físico separado.
Es un identificador único asociado al socio que permite aislar su configuración
y comprobar que cada solicitud corresponde al espacio lógico correcto.

### Endpoints administrativos

| Método y ruta | Qué hace | Quién puede usarlo |
|---|---|---|
| `POST /api/v1/socios` | Registra y aprovisiona un socio. | Ingeniero de Integraciones, servicio interno |
| `GET /api/v1/socios/{socio_id}` | Consulta la configuración vigente. | Ingeniero de Integraciones, servicio interno |
| `PATCH /api/v1/socios/{socio_id}` | Actualiza los campos configurables. | Ingeniero de Integraciones, servicio interno |
| `POST /api/v1/socios/{socio_id}/credenciales` | Genera credenciales técnicas para un socio activo. | Ingeniero de Integraciones, servicio interno |

### Ejemplo de alta

Solicitud para `POST /api/v1/socios`:

```http
Authorization: Bearer <jwt-administrativo>
Content-Type: application/json
```

```json
{
  "nit": "900123456-7",
  "razon_social": "Banco Andes S.A.",
  "contactos_tecnicos": [
    {
      "nombre": "María Torres",
      "correo": "maria.torres@bancoandes.com",
      "telefono": "+573001234567"
    }
  ],
  "pais_operacion": "CO",
  "tipos_seguros_autorizados": [
    "VIAJE",
    "PROTECCION_PAGOS"
  ],
  "endpoints_autorizados": [
    "cotizaciones:crear",
    "polizas:emitir"
  ]
}
```

La respuesta `201 Created` incluye la configuración enviada y los datos
generados por Solventa:

```json
{
  "socio_id": "SOCIO-...",
  "tenant_id": "TENANT-...",
  "estado": "ACTIVO",
  "creado_en": "2026-10-08T00:00:00+00:00",
  "actualizado_en": "2026-10-08T00:00:00+00:00"
}
```

| Respuesta | Cuándo ocurre |
|---|---|
| `201` | El socio fue registrado y aprovisionado. |
| `401` | No se envió un JWT administrativo válido. |
| `403` | El usuario no tiene un rol autorizado. |
| `409` | Ya existe un socio con el NIT enviado. |
| `422` | Faltan campos o la solicitud no cumple el contrato. |

### Consulta y modificación

El `PATCH` permite cambiar razón social, contactos técnicos, país de
operación, tipos de seguro autorizados, endpoints autorizados y estado. Los
identificadores `socio_id` y `tenant_id` no cambian porque conservan la
identidad y el aislamiento del socio.

Cada actualización requiere al menos un cambio y genera una auditoría de tipo
`MODIFICACION` con el actor, la fecha y los campos modificados.

## Interfaz web de registro

El formulario administrativo se encuentra en:

```text
/admin/socios/nuevo
```

La interfaz recopila la información legal, contactos técnicos, país, seguros
y permisos de API. Después del registro muestra el resumen del socio y solicita
sus credenciales mediante
`POST /api/v1/socios/{socio_id}/credenciales`.

El `client_id` y el `client_secret` se muestran en la confirmación con opciones
para copiarlos. La interfaz advierte que el secreto debe guardarse en ese
momento y no lo persiste en el navegador. Si falla la generación, mantiene el
socio creado y permite reintentar solamente ese paso, sin repetir el alta.

## Catálogo de contratos de API

El catálogo inicial define los siguientes scopes. Durante el alta solo deben
seleccionarse las operaciones que el socio necesite.

| Scope | Método y ruta | Uso |
|---|---|---|
| `cotizaciones:crear` | `POST /api/v1/cotizaciones` | Solicitar una cotización. |
| `polizas:emitir` | `POST /api/v1/polizas` | Emitir una póliza desde una cotización aceptada. |

La asociación entre socio, productos y endpoints queda almacenada en su ficha
técnica. Recibir un tenant no concede acceso automático a todas las
operaciones; esto aplica el principio de mínimo privilegio.

## Generación de credenciales

Una vez registrado el socio activo, el Ingeniero de Integraciones solicita sus
credenciales:

```http
POST /api/v1/socios/SOCIO-001/credenciales
Authorization: Bearer <jwt-administrativo>
```

La respuesta `201 Created` contiene:

```json
{
  "socio_id": "SOCIO-001",
  "tenant_id": "TENANT-001",
  "client_id": "solv_cliente_generado",
  "client_secret": "solv_secret_generado",
  "scopes": [
    "cotizaciones:crear"
  ],
  "creado_en": "2026-10-13T00:00:00+00:00"
}
```

El valor de `client_secret` se devuelve únicamente en esta respuesta. La base
de datos conserva su hash, no el secreto en texto plano. El endpoint rechaza la
solicitud cuando el socio no existe o se encuentra inactivo.

## Autenticación OAuth del socio

El backend del socio utiliza el flujo OAuth `client_credentials` para obtener
un token temporal. Envía el `client_id` y el `client_secret` mediante
autenticación HTTP Basic:

```http
POST /api/v1/oauth/token
Authorization: Basic <client_id:client_secret>
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```

La respuesta contiene el JWT y sus scopes:

```json
{
  "access_token": "<jwt-del-socio>",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "cotizaciones:crear"
}
```

La duración predeterminada es de 15 minutos y puede configurarse mediante
`SOCIOS_ACCESS_TOKEN_MINUTES`.

El JWT se firma con RS256 y contiene los claims necesarios para identificar la
integración:

```json
{
  "sub": "solv_cliente_generado",
  "socio_id": "SOCIO-001",
  "tenant_id": "TENANT-001",
  "scope": ["cotizaciones:crear"],
  "type": "partner_access",
  "iat": 0,
  "exp": 0
}
```

Los valores de `iat` y `exp` son marcas de tiempo generadas al emitir el token.
El tipo `partner_access` evita que un JWT de usuario normal sea aceptado como
token de una integración.

## Autorización y aislamiento

La validación interna del gateway recibe el token Bearer y el scope solicitado:

```http
POST /api/v1/autorizaciones/socios
Authorization: Bearer <jwt-del-socio>
X-Scope: cotizaciones:crear
```

Los identificadores del socio y del tenant se extraen del JWT firmado. De esta
forma, cada solicitud queda vinculada a la integración que obtuvo el token y a
su espacio lógico correspondiente.

El módulo comprueba que:

1. la firma y la expiración del token sean válidas;
2. el token sea de tipo `partner_access`;
3. incluya `sub`, `socio_id`, `tenant_id` y `scope`;
4. el scope solicitado esté incluido en el token;
5. el `tenant_id` corresponda al socio;
6. el socio continúe activo;
7. el scope siga autorizado en su configuración vigente.

El contraste con la configuración vigente permite retirar un permiso sin
depender solamente de los datos contenidos en un token emitido previamente.
Las credenciales o tokens faltantes, inválidos o vencidos generan `401`; un
socio inactivo o un scope no autorizado genera `403`.

## Persistencia y auditoría

La información se persiste en PostgreSQL mediante SQLAlchemy.

| Tabla | Contenido |
|---|---|
| `socios_distribucion` | Datos legales, contactos, país, productos, endpoints, estado, identificadores y fechas. |
| `eventos_auditoria_socios` | Alta y modificaciones: actor, acción, campos modificados y fecha. |
| `credenciales_socios` | `client_id`, socio, tenant, hash del secreto, scopes, estado y fecha de creación. |

El NIT y el `tenant_id` son únicos. Los contactos, tipos de seguro, endpoints,
scopes y campos modificados se almacenan como JSON porque forman parte de la
configuración que se consulta como conjunto.

## Pruebas

Las pruebas del módulo están en `backend/tests/socios/` y cubren:

- alta válida, validación de datos y NIT duplicado;
- aprovisionamiento e aislamiento del tenant;
- consulta, modificación y auditoría;
- persistencia de socios y credenciales en PostgreSQL;
- generación del secreto y verificación de su hash;
- entrega administrativa de credenciales;
- intercambio de credenciales válidas por un token OAuth;
- rechazo de secretos incorrectos y socios inactivos;
- firma, expiración, tipo y claims del JWT;
- rechazo de JWT de usuarios usados como tokens de socios;
- autorización por tenant y scope;
- validación de la identidad y el tenant obtenidos desde el JWT.

Las pruebas de la interfaz están en `web/src/` junto a la página y al servicio
de socios. Validan el formulario, la llamada al endpoint de credenciales y la
presentación del secreto.

Para ejecutar las pruebas:

```bash
cd backend
pytest tests/socios
```

```bash
cd web
npm test -- --run
```

## Alcance actual

- El catálogo inicial contiene los contratos de cotización y emisión definidos
  para este sprint y puede ampliarse mediante nuevos elementos del catálogo.
- El aprovisionamiento del tenant es lógico. El `tenant_id` se persiste en
  PostgreSQL, pero no crea recursos de infraestructura separados por socio.
- El flujo implementa la emisión y validación de credenciales. La rotación y
  revocación administrativa no forman parte de los endpoints actuales.

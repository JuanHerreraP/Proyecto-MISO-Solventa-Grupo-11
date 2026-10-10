# Administración de socios de distribución (HU24, BPM-76)

## Qué hace

Este módulo permite que un Ingeniero de Integraciones registre y configure un
socio de distribución, como un banco, una aerolínea o un comercio electrónico.
Durante el alta se crea la ficha técnica del socio, se le asigna un `tenant_id`
lógico y se definen los seguros y contratos de API que puede utilizar.

La configuración queda fuera del núcleo de negocio. Así, dar de alta a un socio
no requiere modificar los servicios de cotización, emisión ni el código del
núcleo de Solventa (EC13).

## Acceso y roles

Los endpoints de administración requieren un JWT válido y uno de estos roles:

- `INGENIERO_INTEGRACIONES`: administra la configuración técnica de socios.
- `SERVICIO_INTERNO`: permite el uso desde procesos internos autorizados.

Un usuario con otro rol recibe `403 Forbidden`. La validación se realiza con la
dependencia `requiere_roles` del módulo de seguridad.

## Flujo de alta

1. El Ingeniero de Integraciones envía la ficha técnica del socio.
2. La API valida los datos obligatorios y que no exista otro registro con el
   mismo NIT.
3. El servicio genera un `socio_id` y aprovisiona un `tenant_id` lógico.
4. La configuración se guarda en PostgreSQL con estado `ACTIVO`.
5. Se registra una auditoría de tipo `ALTA` con el usuario, la fecha y los
   campos creados.

El tenant no representa una nueva base de datos ni un esquema físico. Es un
identificador único asociado al socio que permite aislar su configuración y
validar el consumo de las APIs autorizadas.

## Endpoints de administración

| Método y ruta | Qué hace | Quién puede usarlo |
|---|---|---|
| `POST /api/v1/socios` | Registra y aprovisiona un socio. | Ingeniero de Integraciones, servicio interno |
| `GET /api/v1/socios/{socio_id}` | Consulta la configuración vigente de un socio. | Ingeniero de Integraciones, servicio interno |
| `PATCH /api/v1/socios/{socio_id}` | Actualiza los campos configurables del socio. | Ingeniero de Integraciones, servicio interno |
| `POST /api/v1/autorizaciones/socios` | Valida que un socio activo pueda usar un scope determinado. Es consumido después de la autenticación en el gateway. | Proceso interno o gateway |

### Alta de un socio

Ejemplo de solicitud para `POST /api/v1/socios`:

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

La respuesta `201 Created` incluye, además de la configuración enviada:

```json
{
  "socio_id": "SOCIO-…",
  "tenant_id": "TENANT-…",
  "estado": "ACTIVO",
  "creado_en": "2026-10-08T00:00:00+00:00",
  "actualizado_en": "2026-10-08T00:00:00+00:00"
}
```

| Respuesta | Cuándo ocurre |
|---|---|
| `201` | El socio fue registrado y aprovisionado. |
| `401` | No se envió un token válido. |
| `403` | El usuario no tiene un rol autorizado. |
| `409` | Ya existe un socio con el NIT enviado. |
| `422` | Faltan campos o el formato de la solicitud no es válido. |

### Campos que se pueden actualizar

El `PATCH` permite cambiar razón social, contactos técnicos, país de operación,
tipos de seguro autorizados, endpoints autorizados y estado. Los identificadores
`socio_id` y `tenant_id` no se pueden modificar: conservan la identidad y el
aislamiento del socio después del alta.

Cada actualización requiere al menos un cambio y genera una auditoría de tipo
`MODIFICACION`.

## Catálogo de contratos de API

El catálogo inicial define estos scopes. El formulario o mecanismo de
gobernanza debe seleccionar solo los que el socio necesita.

| Scope | Método y ruta | Uso |
|---|---|---|
| `cotizaciones:crear` | `POST /api/v1/cotizaciones` | Solicitar una cotización. |
| `polizas:emitir` | `POST /api/v1/polizas` | Emitir una póliza desde una cotización aceptada. |

La asociación entre socio, productos y endpoints queda almacenada en la ficha
del socio. Esto aplica el principio de mínimo privilegio: recibir un tenant no
da acceso automático a todas las operaciones de Solventa.

## Validación para el gateway

Después de autenticar las credenciales del socio, el gateway puede consultar:

```http
POST /api/v1/autorizaciones/socios
X-Socio-Id: SOCIO-…
X-Tenant-Id: TENANT-…
X-Scope: cotizaciones:crear
```

El módulo verifica que:

1. el `socio_id` exista;
2. el `tenant_id` corresponda al socio;
3. el socio esté en estado `ACTIVO`;
4. el scope solicitado esté incluido en sus endpoints autorizados.

Si alguna validación falla, la respuesta es `401` para credenciales faltantes o
no válidas, y `403` para un socio inactivo o un scope no autorizado.

## Persistencia y auditoría

La configuración se persiste en PostgreSQL mediante SQLAlchemy.

| Tabla | Contenido |
|---|---|
| `socios_distribucion` | Datos legales, contactos, país, productos, endpoints, estado, IDs y fechas del socio. |
| `eventos_auditoria_socios` | Alta y modificaciones: actor, acción, campos modificados y fecha. |

`nit` y `tenant_id` son únicos. Los contactos, tipos de seguro, endpoints y
campos modificados se almacenan como JSON porque hacen parte de la configuración
del socio y se leen como un conjunto al autorizar o actualizar.

## Pruebas

Las pruebas del módulo están en `backend/tests/socios/` y cubren:

- alta válida y aprovisionamiento del tenant;
- NIT duplicado y datos incompletos;
- consulta y actualización de configuración;
- registro de auditoría;
- aislamiento entre socios y autorización por endpoint;
- persistencia del socio y auditoría en PostgreSQL.

Para ejecutarlas:

```bash
cd backend
pytest tests/socios
```

## Alcance actual

- El catálogo incluye los contratos de cotización y emisión definidos para este
  sprint; se puede ampliar sin alterar la ficha principal del socio.
- El aprovisionador de tenants es lógico y está en memoria. El `tenant_id` sí se
  persiste en PostgreSQL, pero todavía no crea recursos aislados de
  infraestructura por socio.
- El endpoint de autorización recibe las cabeceras que el gateway debe entregar
  después de autenticar al socio. La emisión y administración de credenciales
  OAuth del gateway no forma parte de este módulo.

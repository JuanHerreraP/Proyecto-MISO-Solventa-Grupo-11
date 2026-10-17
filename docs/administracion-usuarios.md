# Administración de usuarios y asignación de roles (HU19)

## Qué hace

Permite al manager de la aplicación, identificado por `SERVICIO_INTERNO`, crear y
listar usuarios de Solventa. El alta administrativa asigna cualquiera de los roles
definidos; no crea nuevas definiciones de roles ni habilita su selección pública.

El registro público continúa asignando `CLIENTE`. Crear una cuenta con rol
`SOCIO_DISTRIBUCION` no crea ni vincula automáticamente una organización: ese
proceso corresponde al [alta de socios](socios-distribucion.md).

## Flujo

1. Un operador autorizado aprovisiona el primer manager en la base de datos; la
   API administrativa requiere un manager existente.
2. El manager inicia sesión y obtiene un access token. En web se utiliza el
   [flujo de cookies y CSRF](sesiones-web.md); para Swagger o un cliente nativo puede
   usar `POST /api/v1/auth/login`.
3. Envía `Authorization: Bearer <access_token>` al listar o crear usuarios.
4. El backend valida la identidad y comprueba el rol `SERVICIO_INTERNO` vigente.
5. Al crear, valida consentimiento, datos y unicidad de correo/documento, consulta
   KYC, genera el hash de contraseña y guarda el rol solicitado.
6. Devuelve los datos públicos del usuario y registra quién lo creó y qué rol asignó.
   Los accesos rechazados y el listado también quedan auditados.
7. El usuario creado inicia sesión con sus credenciales y consulta `/me` para
   obtener su identidad y rol.

## Endpoints

| Método y ruta | Quién | Entrada | Respuesta |
| --- | --- | --- | --- |
| `GET /api/v1/auth/users` | `SERVICIO_INTERNO` | JWT Bearer | 200 con usuarios registrados |
| `POST /api/v1/auth/users` | `SERVICIO_INTERNO` | JWT Bearer y datos de registro más `rol` | 201 con los datos públicos del usuario |
| `GET /api/v1/auth/me` | Usuario autenticado | JWT Bearer | 200 con `id`, nombre, apellido, email y rol propios |

### Ejemplo de creación

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

### Errores

| HTTP | Cuándo |
| --- | --- |
| 401 | Falta un token válido o la sesión expiró/fue revocada |
| 403 | El usuario está inactivo o no tiene el rol requerido |
| 409 | Correo o documento duplicado |
| 422 | Rol desconocido, datos inválidos, falta de consentimiento o KYC rechazado |
| 202 | KYC requiere revisión; no se crea la cuenta |
| 503 | Proveedor KYC no disponible |

## Roles y seguridad

Roles admitidos: `CLIENTE`, `ASESOR_VENTAS`, `ANALISTA_RIESGOS`,
`OPERACIONES_SINIESTROS`, `SOCIO_DISTRIBUCION`, `INGENIERO_INTEGRACIONES`
y `SERVICIO_INTERNO`.

Un `INGENIERO_INTEGRACIONES` puede administrar socios, pero no crear o listar
usuarios mediante estos endpoints. El manager sí puede crear nuevas cuentas
`SERVICIO_INTERNO`. El backend obtiene los permisos del usuario autenticado; una
cabecera `X-Rol` o un campo enviado al registro público no eleva privilegios.

Ver la [matriz de permisos y auditoría](control-acceso-auditoria.md).

## Cómo probar en local

1. Iniciar backend y proveedor KYC según el [README principal](../README.md).
2. Disponer de una cuenta manager aprovisionada por un operador autorizado.
3. Abrir `/docs`, iniciar sesión en `/api/v1/auth/login` y copiar `access_token`.
4. En **Authorize**, pegar el access token y ejecutar el listado y la creación.
5. Repetir con otro rol para comprobar el rechazo 403; sin token debe responder 401.

## Pruebas

Desde `backend`:

```bash
.venv/bin/python -m pytest tests/identidad/tests_sesion/test_api_usuarios_admin.py tests/identidad/tests_sesion/test_api_control_acceso.py
```

Cubren creación de todos los roles, duplicados, rol desconocido, registro público
sin escalamiento, accesos permitidos/denegados y persistencia de auditoría.

## Pendientes conocidos

- No existe una pantalla web para administrar usuarios ni un comando de aprovisionamiento inicial.
- El alta de usuario no vincula una cuenta a la organización de un socio.
- Los proveedores KYC incluidos son simuladores; la integración real está pendiente.

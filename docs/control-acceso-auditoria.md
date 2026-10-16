# Control de acceso y auditoría (HU19, EC08)

## Qué hace

Las APIs obtienen la identidad de un JWT firmado y consultan el rol vigente en la
base de datos. La cabecera `X-Rol` no concede permisos. Se usa `requiere_roles`
tanto para socios y administración de usuarios como para perfilamiento,
enriquecimiento y verificación KYC directa.

## Flujo

1. El cliente envía el access token en `Authorization: Bearer <access_token>`.
2. El backend valida firma, expiración, usuario activo y vigencia de su sesión.
3. Consulta el rol actual en persistencia y verifica los roles permitidos.
4. Si opera un cliente, comprueba que la oferta o el consentimiento le pertenezcan.
5. Rechaza una identidad inválida con 401 o permisos insuficientes con 403, antes
   de consultar o modificar el recurso.
6. Registra el resultado y los datos de auditoría sin incluir tokens ni contraseñas.
7. En web, la ruta consulta `/me` antes de montar la pantalla; ocultar opciones no
   sustituye la validación de la API.

## Endpoints y permisos

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

## Registro de eventos

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

## Cómo probar en local

1. Iniciar la API y autenticar una cuenta de cada rol mediante los contratos de
   [identidad](identidad-autenticacion.md) o [sesión web](sesiones-web.md).
2. Consultar `/api/v1/auth/me` para comprobar el `id` y el rol efectivos.
3. Ejecutar las operaciones de la matriz con Bearer y verificar 200/201, 401 o 403.
4. Como cliente, cambiar el `cliente_id` de oferta o consentimiento y comprobar 403.
5. Revisar los registros de `eventos_autenticacion` en la base de datos del ambiente.

## Pruebas

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

## Pendientes conocidos

- No hay un modelo de asignación de clientes a asesores; los roles internos conservan
  acceso transversal conforme a la matriz.
- No existe una pantalla ni un endpoint de consulta de auditoría.
- Si falla la escritura de auditoría, se registra el error en el logger y continúa
  la operación; no hay una cola persistente de reintentos.

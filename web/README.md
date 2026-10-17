# Solventa Web

## Qué hace

Portal web de Solventa desarrollado con React, TypeScript y Vite. Incluye registro
con validación KYC, inicio de sesión, restauración y renovación de sesión, Home
según el rol y alta de socios de distribución con generación de credenciales.

El registro público crea cuentas `CLIENTE`. Los usuarios internos se crean desde
la API administrativa por un manager con rol `SERVICIO_INTERNO`; todavía no hay una
pantalla web para administrar usuarios.

## Flujo

1. El usuario se registra en `/registro`, autoriza la validación de identidad y
   recibe el resultado del backend. Si el registro es exitoso, vuelve al login.
2. En `/login`, la web obtiene un reto CSRF y envía correo y contraseña. El backend
   establece el refresh token en una cookie HttpOnly y devuelve el access token.
3. La web conserva el access token en memoria y consulta `/api/v1/auth/me` para
   verificar la sesión y el rol antes de mostrar una ruta protegida.
4. Home permite cerrar sesión. `INGENIERO_INTEGRACIONES` y `SERVICIO_INTERNO` ven
   además “Crear un nuevo socio”.
5. El formulario registra la ficha técnica del socio y solicita sus credenciales.
   El secreto se muestra únicamente en el resultado de generación.
6. Al recargar, la web restaura la sesión mediante la cookie. Mientras hay actividad,
   renueva el access token; tras 30 minutos de inactividad vuelve al login.

## Pantallas y roles

| Ruta | Acceso | Función |
| --- | --- | --- |
| `/` | Público | Redirige a `/login` |
| `/login` | Público | Ingreso con correo y contraseña |
| `/registro` | Público | Registro de un cliente con consentimiento KYC |
| `/home` | Cualquier usuario con sesión válida | Inicio, cierre de sesión y navegación según rol |
| `/admin/socios/nuevo` | `INGENIERO_INTEGRACIONES`, `SERVICIO_INTERNO` | Alta de socios y generación de credenciales |

`RutaProtegida` consulta `/me` antes de montar las pantallas. Sin sesión redirige
al login; sin el rol requerido vuelve a Home con un aviso. La misma comprobación
se aplica al escribir la URL directamente, recargar y navegar con atrás/adelante.
El backend valida sus propios permisos en cada operación.

## Endpoints

| Método y ruta | Uso en la web |
| --- | --- |
| `POST /api/v1/auth/register` | Registro público; KYC y asignación de `CLIENTE` |
| `GET /api/v1/auth/web/csrf` | Obtener el reto CSRF |
| `POST /api/v1/auth/web/login` | Iniciar sesión con cookies protegidas |
| `POST /api/v1/auth/web/refresh` | Restaurar o renovar la sesión y rotar el refresh |
| `POST /api/v1/auth/web/logout` | Revocar la sesión y eliminar las cookies |
| `GET /api/v1/auth/me` | Consultar el usuario autenticado y su rol |
| `POST /api/v1/socios` | Registrar y aprovisionar un socio |
| `POST /api/v1/socios/{socio_id}/credenciales` | Generar sus credenciales de integración |

El login web recibe `email` y `password`. La respuesta contiene `access_token`,
`token_type`, `expires_in` y `csrf_token`; el refresh no aparece en el JSON.
Los endpoints nativos `/api/v1/auth/login`, `/refresh` y `/logout` mantienen el
contrato para Android, pero no son los que utiliza este cliente web.

Los contratos completos están en [sesiones web](../docs/sesiones-web.md),
[identidad](../docs/identidad-autenticacion.md) y
[socios de distribución](../docs/socios-distribucion.md).

## Manejo de sesión y seguridad

- Access token en memoria; refresh en cookie `HttpOnly`, `Secure` y `SameSite`.
  No se guardan tokens en localStorage ni sessionStorage.
- Las operaciones de sesión usan `credentials: include` y `X-CSRF-Token`; el
  backend valida el reto y el origen. Las APIs protegidas usan Bearer y omiten cookies.
- La aplicación espera la restauración antes de montar las páginas. Las rutas
  protegidas vuelven a comprobar el rol vigente mediante `/me`.
- El access token dura 30 minutos. Se renueva cuando queda un minuto o se detecta
  expiración; las peticiones concurrentes comparten la renovación.
- La web mide interacción y el backend registra actividad por sesión. Tras 30
  minutos de inactividad, la sesión ya no puede renovarse.
- Logout revoca la sesión, elimina las cookies y limpia la memoria. Si falla,
  Home muestra un error y permite reintentar.

## Configuración y ejecución local

### Requisitos

Node.js 24 y npm; Python 3.12 para el backend. Las dependencias se instalan desde
los archivos de bloqueo y requisitos del repositorio.

### Backend y KYC

Preparar el backend siguiendo el [README principal](../README.md#backend-en-local).
Para probar el registro, iniciar también el proveedor KYC A en otra terminal,
desde `backend`:

```bash
.venv/bin/uvicorn mocks.kyc.provider_a:app --reload --port 8001
```

Levantar la API para desarrollo HTTP local, también desde `backend`:

```bash
WEB_COOKIE_SECURE=false WEB_ALLOWED_ORIGINS=http://localhost:5173 .venv/bin/uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` y Swagger en `http://localhost:8000/docs`.
Los proveedores KYC incluidos son simuladores; no verifican identidades reales.

### Cliente web

Desde `web`:

```bash
npm ci
cp .env.example .env
npm run dev
```

El archivo `.env` debe contener:

```env
VITE_API_URL=http://localhost:8000
```

Abrir `http://localhost:5173`. Usar el mismo hostname para web y API: no mezclar
localhost con 127.0.0.1. Si cambia el puerto u origen de la web, actualizar
`WEB_ALLOWED_ORIGINS` y reiniciar el backend. Reiniciar Vite tras cambiar `.env`.

### Producción

Usar HTTPS, `APP_ENV=production`, `WEB_COOKIE_SECURE=true` y una lista explícita
de orígenes en `WEB_ALLOWED_ORIGINS`; no se admiten comodines. El valor predeterminado
de `WEB_COOKIE_SAMESITE` es `lax`. Configurar `VITE_API_URL` antes de compilar.
No colocar secretos en variables `VITE_*`, que forman parte del cliente distribuido.

Ver [configuración de cookies y CORS](../docs/sesiones-web.md#configuración) y
[backend/.env.example](../backend/.env.example). El backend no carga `.env`
automáticamente; las variables deben pasarse al proceso.

## Estructura principal

| Archivo o carpeta | Responsabilidad |
| --- | --- |
| `src/App.tsx` | Restauración inicial, control de sesión y rutas |
| `src/components/auth/AuthLayout.tsx` | Presentación compartida de login y registro |
| `src/components/auth/RutaProtegida.tsx` | Validación de sesión y roles antes de montar una pantalla |
| `src/pages/` | Login, registro, Home y alta de socios |
| `src/services/auth.service.ts` | Registro, login y consulta de `/me` |
| `src/services/session.ts` | Access token en memoria, renovación, inactividad y logout |
| `src/services/web-session.ts` | Cookies, reto CSRF y coordinación de operaciones de sesión |
| `src/services/socios.service.ts` | Alta del socio y generación de credenciales |
| `src/types/` | Contratos TypeScript y roles habilitados para administrar socios |
| `src/styles/` | Estilos de autenticación y socios |
| `src/test/setup.ts` | Configuración compartida de pruebas |

## Tecnologías y sistema visual

React, TypeScript, Vite y React Router; Vitest, React Testing Library, User Event
y jsdom para pruebas; ESLint para análisis y V8 para cobertura.

La interfaz utiliza Plus Jakarta Sans y DM Sans, con Material Symbols Outlined.

| Uso | Color |
| --- | --- |
| Estructura principal | `#101B32` |
| Navegación y foco | `#3867F2` |
| Acción principal | `#A7E451` |
| Información | `#29B4D3` |
| Atención | `#F69A4A` |

## Pruebas y validación

Desde `web`:

```bash
npm test -- --run
npm test -- --run --coverage
npm run lint
npm run build
```

`npm test` abre el modo interactivo. La cobertura HTML queda en `coverage/` y la
compilación en `dist/`; `npm run preview` permite revisar esa compilación localmente.

Las pruebas cubren registro y errores, login con CSRF, restauración, renovación,
inactividad, logout, botones por rol, acceso directo a rutas protegidas, alta de
socios y llamadas autenticadas. El backend tiene pruebas independientes para los
atributos de cookies, CORS, CSRF, permisos y persistencia de auditoría.

## Documentación relacionada

- [Índice técnico](../docs/README.md).
- [Administración de usuarios y roles](../docs/administracion-usuarios.md).
- [Control de acceso y auditoría](../docs/control-acceso-auditoria.md).
- [Sesión web](../docs/sesiones-web.md).
- [Cliente Android e ingreso biométrico](../docs/inicio-sesion-biometrico.md).

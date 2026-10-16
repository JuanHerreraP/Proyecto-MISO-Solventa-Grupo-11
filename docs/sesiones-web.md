# Sesión web con cookies protegidas (HU19)

## Qué hace

La web conserva el access token únicamente en memoria y envía
`Authorization: Bearer <access_token>` a los recursos protegidos. El refresh token
se guarda únicamente en una cookie del backend: no se devuelve en el JSON web ni
se guarda en localStorage o sessionStorage.

La cookie utiliza `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` y no tiene Domain.
Con Secure habilitado se llama `__Host-solventa_refresh`; el prefijo impide cookies
con Domain o con un Path diferente. Una segunda cookie HttpOnly almacena el reto
CSRF. El backend emite y elimina las cookies; React no puede leerlas.

## Flujo

1. Al abrir la aplicación, intenta restaurar la sesión mediante la cookie y espera
   el resultado antes de montar las pantallas.
2. Para iniciar sesión, obtiene el reto CSRF y envía correo y contraseña al login web.
3. El backend establece las cookies y devuelve el access token; React consulta
   `/api/v1/auth/me` y muestra las rutas permitidas para el rol.
4. Antes de que venza el access token, solicita una renovación. El backend rota
   el refresh y actualiza la cookie.
5. Tras 30 minutos sin actividad, la sesión deja de ser válida y vuelve al login.
6. Al cerrar sesión, el backend revoca la sesión y elimina ambas cookies.

## Endpoints

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

## Restauración, renovación y cierre

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

## Inactividad

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

## Configuración

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

## Pruebas

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

## Pendientes conocidos

- La persistencia requiere cookies habilitadas y una configuración de origen y HTTPS
  compatible con el navegador; los sitios distintos pueden requerir SameSite=None.
- Web Locks y BroadcastChannel dependen del soporte del navegador. La renovación
  dentro de cada pestaña sigue compartiendo una sola petición.

# HU06 — Ubicar prestadores cercanos y solicitar asistencia en sitio

Permite al **Cliente Asegurado** encontrar, sobre un mapa y una lista, prestadores de asistencia
cercanos compatibles con una de sus pólizas vigentes, y solicitar asistencia en sitio. También
consultar y cancelar sus solicitudes.

Esta funcionalidad es **móvil (Android) + backend**. No tiene pantalla web ni portal
administrativo de prestadores.

## Alcance y decisiones de diseño

- **No se agregó un ramo nuevo.** HU06 trabaja con los ramos actuales
  (`VIAJE`, `PROTECCION_DISPOSITIVOS`, `VIDA`, `PARAMETRICO`). Solo `VIAJE` y
  `PROTECCION_DISPOSITIVOS` ofrecen asistencia inicialmente; `VIDA` y `PARAMETRICO` devuelven una
  lista de servicios vacía, lo cual no es un error.
- **No se implementó interfaz web.** El portal React no se tocó.
- **No se creó un CRUD administrativo de prestadores.** Los prestadores de demostración se
  precargan con un *seed* idempotente.
- **No se exige ni se crea automáticamente un siniestro.** Una asistencia no requiere HU04/HU20.
  El modelo deja `siniestro_id` anulable solo para una evolución futura; `NULL` es válido.

## Servicios de asistencia por ramo

| Ramo | Servicios |
|---|---|
| `VIAJE` | `ASISTENCIA_MEDICA` (Atención médica), `ASISTENCIA_VIAJERO` (Asistencia al viajero) |
| `PROTECCION_DISPOSITIVOS` | `DIAGNOSTICO_TECNICO` (Diagnóstico técnico), `REPARACION_DISPOSITIVO` (Reparación de dispositivo) |
| `VIDA` | — |
| `PARAMETRICO` | — |

La relación está en `SERVICIOS_POR_RAMO` (`backend/app/asistencias/modelos.py`). No se modifica
`RamoPoliza`.

## Arquitectura

```text
ANDROID (Kotlin / Compose)
  AssistanceScreen + MapaPrestadores
        → AsistenciasViewModel
        → AsistenciasCoordinator (reglas, sin Android)
        → RemoteAsistenciasGateway → Retrofit
                                        │
BACKEND (FastAPI)                       ▼
  app/api/asistencias.py, app/api/prestadores.py
        → ServicioAsistencias (validaciones de póliza y prestador)
        → RepositorioPrestadores / RepositorioAsistencias / RepositorioPolizas
        → SQLAlchemy → PostgreSQL / SQLite
```

Se respeta la separación API → Servicio → Repositorio → Persistencia. No hay SQL en los routers.

### Backend

```text
backend/app/asistencias/
├── modelos.py        # TipoServicioAsistencia, SERVICIOS_POR_RAMO, Prestador,
│                     # EstadoAsistencia, SolicitudAsistencia, NuevaAsistencia, distancia_km
├── modelos_db.py     # PrestadorDB, PrestadorServicioDB (normalizado), AsistenciaDB
├── repositorio.py    # Protocolos + implementaciones EnMemoria y Postgres
├── servicio.py       # ServicioAsistencias + excepciones de dominio
└── vistas.py         # Modelos de respuesta
backend/app/api/
├── asistencias.py    # GET servicios, POST crear, GET listar, POST cancelación
└── prestadores.py    # GET prestadores cercanos
backend/sembrar_prestadores.py   # seed idempotente de prestadores demo
```

### Modelo de prestadores (relación conceptual)

```text
Póliza → Ramo → Servicios disponibles → Prestadores que ofrecen ese servicio
```

Los prestadores **no** se copian dentro de cada póliza. Sus servicios se guardan normalizados en
`prestador_servicios` (una fila por servicio), no como una cadena separada por comas.

Tablas nuevas: `prestadores`, `prestador_servicios`, `asistencias`.

## Endpoints

Todos requieren rol `CLIENTE`. El `cliente_id` sale de la sesión/JWT: la app nunca lo envía.
Todas las respuestas llevan `Cache-Control: no-store` y `Pragma: no-cache`.

### `GET /api/v1/asistencias/servicios?poliza_id=POL-001`

```json
{
  "poliza_id": "POL-001",
  "ramo": "PROTECCION_DISPOSITIVOS",
  "servicios": [
    { "codigo": "DIAGNOSTICO_TECNICO", "nombre": "Diagnóstico técnico" },
    { "codigo": "REPARACION_DISPOSITIVO", "nombre": "Reparación de dispositivo" }
  ]
}
```

### `GET /api/v1/prestadores/cercanos`

Query: `poliza_id`, `servicio`, `latitud`, `longitud`, `radio_km` (default 25, mínimo 1, máximo
100). Devuelve los prestadores activos que ofrecen el servicio, dentro del radio, ordenados del
más cercano al más lejano.

```json
{
  "poliza_id": "POL-001",
  "servicio": "REPARACION_DISPOSITIVO",
  "ubicacion": { "latitud": 4.711, "longitud": -74.072 },
  "prestadores": [
    { "prestador_id": "PREST-TEC-001", "nombre": "Solventa Tech Centro",
      "tipo_servicio": "REPARACION_DISPOSITIVO", "direccion": "...",
      "telefono": "3000000001", "latitud": 4.715, "longitud": -74.069, "distancia_km": 0.55 }
  ]
}
```

### `POST /api/v1/asistencias`

Cuerpo: `poliza_id`, `prestador_id`, `servicio`, `latitud`, `longitud`, `observaciones?`.
Nunca se envían `cliente_id`, `estado` ni `creada_en`. Responde `201` con la asistencia creada en
estado `SOLICITADA`.

### `GET /api/v1/asistencias`

Lista las asistencias del cliente, de la más reciente a la más antigua. Incluye el seguimiento:
`estado` (`SOLICITADA`, `ACEPTADA` o `CANCELADA`), `aceptada_en` y `tiempo_estimado_llegada_minutos`
(ambos `null` hasta que Operaciones acepte / registre el ETA).

### `POST /api/v1/asistencias/{asistencia_id}/cancelacion`

Cambia `SOLICITADA → CANCELADA` (y también `ACEPTADA → CANCELADA`) y registra `cancelada_en`. No
elimina el registro. Solo el propietario puede cancelar; una asistencia ya cancelada responde
`409`. (Se conserva la regla existente: el cliente puede cancelar mientras la asistencia no esté
ya cancelada.)

## Seguimiento operativo (rol Operaciones/Siniestros)

El rol **`OPERACIONES_SINIESTROS`** (ya existente en el proyecto; no se creó un rol nuevo) consulta
y da seguimiento a las solicitudes. El cliente **no** tiene acceso a estos endpoints. Todos
responden `Cache-Control: no-store` y no exponen datos personales del cliente más allá de su
identificador.

### `GET /api/v1/operaciones/asistencias`

Lista las solicitudes para seguimiento, de la más reciente a la más antigua. Filtros opcionales:
`estado`, `poliza_id`, `prestador_id`.

### `GET /api/v1/operaciones/asistencias/{asistencia_id}`

Detalle para seguimiento: añade `cliente_id`, `numero_poliza`, `aceptada_en` y
`tiempo_estimado_llegada_minutos`.

### `POST /api/v1/operaciones/asistencias/{asistencia_id}/aceptacion`

Acepta una asistencia `SOLICITADA` (`SOLICITADA → ACEPTADA`), fija `aceptada_en` y, si se envía,
el ETA. El ETA es **opcional**: `{}` es válido ("aún no disponible").

```json
{ "tiempo_estimado_llegada_minutos": 20 }
```

### `PATCH /api/v1/operaciones/asistencias/{asistencia_id}/seguimiento`

Actualiza el ETA de una asistencia ya `ACEPTADA` (puede ponerlo o dejarlo en `null`). Si la
asistencia no está `ACEPTADA`, responde `409 TRANSICION_ESTADO_INVALIDA`.

### Estados y ETA

- Estados: `SOLICITADA`, `ACEPTADA`, `CANCELADA`.
- `tiempo_estimado_llegada_minutos` es opcional (`null` = aún no disponible; nunca `0`/`-1`), con
  rango válido 1–1440 minutos. No se calcula automáticamente (no hay Directions API ni tracking
  GPS del prestador): es un dato operativo que registra Operaciones.
- Transiciones: solo `SOLICITADA → ACEPTADA`; aceptar dos veces o aceptar una cancelada es `409`.

### Códigos de error

| Código | HTTP |
|---|---|
| `POLIZA_NO_ENCONTRADA` | 404 |
| `POLIZA_NO_AUTORIZADA` | 403 |
| `POLIZA_NO_VIGENTE` | 409 |
| `SERVICIO_NO_DISPONIBLE` | 422 |
| `PRESTADOR_NO_ENCONTRADO` | 404 |
| `PRESTADOR_NO_DISPONIBLE` | 409 |
| `SERVICIO_NO_OFRECIDO_POR_PRESTADOR` | 422 |
| `RADIO_INVALIDO` | 422 |
| `ASISTENCIA_NO_ENCONTRADA` | 404 |
| `ASISTENCIA_NO_AUTORIZADA` | 403 |
| `ASISTENCIA_YA_CANCELADA` | 409 |
| `ASISTENCIA_YA_ACEPTADA` | 409 |
| `ASISTENCIA_CANCELADA` | 409 |
| `TRANSICION_ESTADO_INVALIDA` | 409 |
| (sin token) | 401 |
| (rol no autorizado) | 403 |

## Cálculo de distancia

`distancia_km(lat1, lon1, lat2, lon2)` en `backend/app/asistencias/modelos.py` implementa la
fórmula de **Haversine**. Es una función pura y determinista; no se usa PostGIS. Devuelve `0.0`
cuando los puntos coinciden. Está cubierta por pruebas unitarias.

## Android

| Paquete | Contenido |
|---|---|
| `domain/asistencias` | `AsistenciasCoordinator` (flujo por pasos, sin Android), `Modelos` (`TipoServicio`, `EstadoAsistencia`, `Asistencia`, `PrestadorCercano`, el puerto `AsistenciasGateway`, `EstadoAsistencias`, `MensajesAsistencias`). |
| `data/remote` | `AsistenciasApi` (Retrofit), `AsistenciasDtos` (Gson, anulables + mapeo), `RemoteAsistenciasGateway`. |
| `data/local` | `FuenteUbicacionActual` + `FuenteUbicacionFused` (ubicación actual con `FusedLocationProviderClient`, cae a la última conocida de `ProveedorUbicacion`). |
| `ui/asistencias` | `AsistenciasViewModel` (+ `Fabrica`). |
| `ui/screens` | `AssistanceScreen` (flujo completo) y `MapaPrestadores` (el `GoogleMap`, aislado). |

El flujo: seleccionar póliza → seleccionar servicio → permitir ubicación → ver mapa + lista →
seleccionar prestador → confirmar → éxito → mis asistencias / cancelar. La ubicación se obtiene en
el ViewModel y se le pasa al coordinador; la pantalla nunca toca el GPS. Las pólizas elegibles
salen de la billetera (vigentes de `VIAJE` o `PROTECCION_DISPOSITIVOS`); el backend revalida.

En **Mis asistencias**, cada tarjeta muestra el seguimiento según el estado: `SOLICITADA`
("Esperando aceptación del prestador."), `ACEPTADA` ("El prestador aceptó tu solicitud." +
"Tiempo estimado de llegada: N min" o "Aún no disponible" cuando el ETA es `null`) y `CANCELADA`
(sin ETA activo). El botón de cancelar solo aparece cuando la asistencia está `SOLICITADA`.

### Configuración del mapa y de la API key

Se usa **Google Maps SDK for Android + Maps Compose**. La clave **no se versiona**. El build la
lee, en este orden, y la inyecta como `manifestPlaceholders["mapsApiKey"]` en la `meta-data
com.google.android.geo.API_KEY` del manifiesto:

1. `android/local.properties` → `solventa.mapsApiKey=...` (archivo **no versionado**; recomendado
   para desarrollo local).
2. propiedad de Gradle `-Psolventa.mapsApiKey=...` (línea de comandos / CI).

La clave **no debe ir en `android/gradle.properties`**, porque ese archivo **sí** está en Git.
Sin clave, el build compila (CI no necesita una clave real), pero el mapa aparece **en blanco**
(se ven el logo de Google y los controles de zoom, pero no cargan los mosaicos); la lista de
prestadores sigue funcionando.

En `android/local.properties`:

```properties
sdk.dir=/ruta/a/Android/Sdk
solventa.mapsApiKey=MI_CLAVE
```

O por línea de comandos:

```bash
./gradlew assembleDebug -Psolventa.mapsApiKey=MI_CLAVE
```

La clave debe ser de tipo **Maps SDK for Android** en Google Cloud. Si tiene restricción de
aplicaciones Android, debe registrar el *package name* `com.example.solventa` y el SHA-1 del
certificado (debug o release) que firma el APK. El SHA-1 debug se obtiene con
`./gradlew signingReport` (variante `debug`). Tras cambiar la clave, reinstala la app
(`./gradlew installDebug` o re-ejecuta desde Android Studio) para que el nuevo manifiesto surta
efecto.

### Permiso de ubicación

Se reutilizan los permisos existentes (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, ya en el
manifiesto) y el `ProveedorUbicacion` de HU04. Si el cliente rechaza el permiso, la app no se
cierra: muestra el aviso y ofrece **Reintentar**. No se envían coordenadas ficticias. HU06 solo
pide la ubicación al buscar asistencia; no hay rastreo continuo ni en segundo plano.

## Privacidad

Las coordenadas se guardan únicamente donde son necesarias para prestar la asistencia. No se
registran en logs, mensajes de error ni analítica.

## Seed de prestadores demo

```bash
cd backend
python sembrar_prestadores.py
```

Es idempotente. Crea 14 prestadores de demostración con coordenadas en **Bogotá**, **Mosquera** y
**Madrid** (Cundinamarca), más uno en Medellín (fuera del radio) y uno inactivo, para ilustrar los
casos de filtrado.

| ID | Nombre | Servicios | Coordenadas | Caso |
|---|---|---|---|---|
| PREST-TEC-001 | Solventa Tech Centro | reparación, diagnóstico | 4.7150, -74.0690 | cerca (Bogotá) |
| PREST-TEC-002 | TechCare Norte | reparación | 4.6860, -74.0480 | algo más lejos |
| PREST-TEC-003 | Mosquera Dispositivos | diagnóstico, reparación | 4.7059, -74.2302 | Mosquera |
| PREST-TEC-004 | Lejos Tech Medellín | reparación | 6.2518, -75.5636 | fuera del radio |
| PREST-TEC-005 | Inactivo Tech | reparación, diagnóstico | 4.7130, -74.0700 | inactivo (no aparece) |
| PREST-VIA-001 | Centro Médico Aliado | médica | 4.7120, -74.0660 | cerca (viaje) |
| PREST-VIA-002 | Asistencia Viajero 24/7 | viajero, médica | 4.6980, -74.1050 | viaje |
| PREST-VIA-003 | Mosquera Salud Viajero | viajero | 4.7090, -74.2250 | Mosquera (viaje) |
| PREST-MAD-001 | Solventa Asistencia Madrid | reparación, diagnóstico, médica | 4.7328, -74.2635 | Madrid (Cundinamarca) |
| PREST-MAD-002 | Centro Técnico Madrid | diagnóstico, reparación | 4.7285, -74.2710 | Madrid (dispositivos) |
| PREST-MAD-003 | Asistencia Occidente | viajero, médica | 4.7410, -74.2550 | Madrid (viaje) |
| PREST-BOG-001 | Solventa Bogotá Centro | reparación, diagnóstico, médica | 4.7115, -74.0700 | centro de Bogotá |
| PREST-BOG-002 | Centro Médico Bogotá | médica, viajero | 4.7180, -74.0660 | centro de Bogotá (viaje) |
| PREST-BOG-003 | TechCare Bogotá | reparación, diagnóstico | 4.7000, -74.0800 | sur del centro de Bogotá |

### Coordenadas de referencia para la demo

- **Bogotá (centro):** `4.7110, -74.0721`
- **Mosquera (Cundinamarca):** `4.7059, -74.2302`
- **Madrid (Cundinamarca):** `4.7328, -74.2635`

## Prueba manual

1. Siembra pólizas: `CLIENTE_EMAIL=tu-correo python sembrar_polizas.py`
   (crea una de `PROTECCION_DISPOSITIVOS` y una de `VIAJE` vigentes).
2. Siembra prestadores: `python sembrar_prestadores.py`.
3. Levanta el backend: `uvicorn app.main:app --reload`.
4. Configura la ubicación del emulador cerca de Bogotá (`4.7110, -74.0721`) desde los controles
   extendidos del emulador (Location).
5. Abre Solventa, inicia sesión y entra a **«Asistencia en sitio»** desde el inicio.
6. Elige la póliza de dispositivos → **Reparación de dispositivo** → permite la ubicación.
7. Revisa el mapa y la lista de prestadores cercanos, ordenados por distancia.
8. Selecciona **Solventa Tech Centro**, agrega una observación y **Solicitar asistencia**.
9. Verifica el estado `SOLICITADA` y, en **Mis asistencias**, **Cancela** la solicitud.

## Limitaciones

- La visualización del mapa requiere una clave de Google Maps; sin ella la lista funciona pero el
  mapa no muestra mosaicos.
- Los prestadores son datos de demostración controlados por Solventa; no hay integración con
  directorios externos.
- El ciclo de vida de la asistencia es `SOLICITADA` → `ACEPTADA` → (o `CANCELADA`). El seguimiento
  operativo se limita al estado y al tiempo estimado de llegada que registra Operaciones; no hay
  tracking GPS del prestador en tiempo real, cálculo automático de rutas, pagos ni calificación
  (fuera de alcance).

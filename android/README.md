# Solventa - Aplicación Android

Aplicación móvil nativa de **Solventa** desarrollada en Kotlin con Jetpack Compose, estructurada bajo una arquitectura modular y reactiva.

---

## 🏗️ Estructura del Proyecto

```text
app/src/main/java/com/example/solventa/
├── MainActivity.kt                # Punto de entrada de la app
├── ui/
│   ├── components/                # Componentes reutilizables de UI
│   │   ├── PrimaryButton.kt       # Botón principal estilizado
│   │   ├── SecondaryButton.kt     # Botón secundario estilizado
│   │   ├── TextField.kt           # Campo de texto personalizado
│   │   └── NoticePill.kt          # Píldoras de notificación/alerta
│   ├── navigation/                # Navegación
│   │   ├── NavGraph.kt            # Grafo de navegación principal
│   │   └── ScreenRoute.kt         # Rutas fuertemente tipadas
│   ├── screens/                   # Pantallas de la aplicación
│   │   ├── WelcomeScreen.kt       # Pantalla de bienvenida
│   │   ├── BiometricalLoginScreen.kt  # Ingreso biométrico
│   │   ├── CredentialsLoginScreen.kt # Ingreso por credenciales
│   │   └── RegisterScreen.kt      # Pantalla de registro (BPM-22)
│   └── theme/                     # Sistema de diseño de la marca
│       ├── Color.kt               # Paleta de colores
│       ├── Theme.kt               # Configuración de SolventaTheme
│       └── Type.kt                # Tipografías (Plus Jakarta Sans y DM Sans)
```

---

## 🎨 Sistema de Diseño y Tema

La interfaz de usuario implementa el sistema de diseño oficial de la marca Solventa a través de **`SolventaTheme`**:
- **Tipografías:**
  - **Plus Jakarta Sans:** Utilizada para titulares, encabezados y títulos principales.
  - **DM Sans:** Utilizada para textos de cuerpo, etiquetas e insumos de lectura.
- **Componentes Atómicos:** `PrimaryButton`, `SecondaryButton`, `TextField` y `NoticePill` garantizan consistencia visual y accesibilidad en toda la experiencia de usuario.

---

## 🧭 Flujo de Navegación (`NavGraph`)

La navegación utiliza **Jetpack Navigation Compose** mediante rutas selladas en `ScreenRoute`:

| Ruta (`ScreenRoute`) | Pantalla (`Screen`) | Descripción |
|---|---|---|
| `welcome_screen` | `WelcomeScreen` | Pantalla de inicio de bienvenida con accesos principales |
| `biometrical_login_screen` | `BiometricalLoginScreen` | Inicio de sesión rápido mediante autenticación biométrica |
| `credentials_login_screen` | `CredentialsLoginScreen` | Inicio de sesión tradicional con correo y contraseña |
| `register_screen` | `RegisterScreen` | Registro de nuevos usuarios y captura de datos de identidad (BPM-22) |
| `home_screen` | `HomeScreen` | Inicio del cliente; solo se muestra con sesión autenticada (BPM-23) |
| `wallet_screen` | `WalletScreen` | Billetera de pólizas, vigentes e inactivas (BPM-31) |
| `certificate_screen/{polizaId}` | `CertificateScreen` | Certificado con QR y opción de compartir (BPM-31) |
| `claims_screen` | `ClaimsScreen` | Lista de siniestros del cliente: manuales y automáticos de telemetría (HU20) |
| `claim_form_screen` | `ClaimFormScreen` | Formulario de registro manual de un siniestro (HU20) |

---

## 🔐 Inicio de sesión biométrico (HU02, BPM-23)

| Paquete | Contenido |
|---|---|
| `domain/auth` | `AuthCoordinator`: reglas del ingreso biométrico, el fallback, la expiración y el cierre de sesión. Sin dependencias de Android. |
| `biometric` | `AutenticadorBiometrico` (`BiometricPrompt`) y la traducción de sus códigos de error. |
| `data/session` | `KeystoreBovedaSesion`: guarda el refresh token cifrado con una llave del Keystore que exige biometría. |
| `data/remote` | Cliente Retrofit de `/api/v1/auth` (login, refresh, logout, me). |
| `ui/auth` | `AuthViewModel`, que expone el estado a las pantallas. |

La URL del backend sale de `BuildConfig.API_BASE_URL` (por defecto `http://10.0.2.2:8000/`). Detalle completo en [docs/inicio-sesion-biometrico.md](../docs/inicio-sesion-biometrico.md).

## 👛 Billetera digital de pólizas (HU07, BPM-31)

| Paquete | Contenido |
|---|---|
| `domain/polizas` | `BilleteraCoordinator`: carga de la billetera, certificado, enlace para compartir y limpieza al cerrar sesión. `Formatos`: fechas y dinero sin `java.time`. |
| `data/remote` | Cliente Retrofit de `/api/v1/billetera` y su gateway. |
| `ui/billetera` | `BilleteraViewModel` y el texto e intent para compartir. |
| `ui/components/CodigoQr.kt` | QR dibujado en Compose con ZXing, sin red. |

Para ver pólizas en la app, siembra datos de prueba con `backend/sembrar_polizas.py`. Detalle en [docs/billetera-digital.md](../docs/billetera-digital.md).

## ⚠️ Siniestros del cliente (HU20)

Pantalla de solo lectura que lista los siniestros del cliente autenticado, del más reciente al
más antiguo. Incluye los **automáticos** creados por la telemetría externa (retraso de vuelo,
clima) y los manuales. El backend filtra por la identidad del token: la app nunca envía un
identificador de cliente.

Desde la lista, con **«Reportar siniestro»** se abre un formulario (`ClaimFormScreen`) que
registra un siniestro manual vía `POST /api/v1/siniestros`: se elige una de las pólizas vigentes
de la billetera (o se ingresa el número), la fecha/hora del evento, el lugar, la descripción y la
estimación del daño. La validación local es ayuda temprana; el backend valida de forma
autoritativa la vigencia y la titularidad y responde 403/404/409/422 con un código que se traduce
a un mensaje claro. Al registrar bien, la app recarga la lista y vuelve a ella.

| Paquete | Contenido |
|---|---|
| `domain/siniestros` | `SiniestrosCoordinator`: carga de la lista, **registro manual** (`registrar`) con mapeo de errores y recarga, y limpieza al cerrar sesión. `Modelos`: `Siniestro`, `Siniestros`, `SolicitudSiniestro`, `OrigenSiniestro`, `EstadoSiniestro` y el puerto `SiniestrosGateway`. Sin dependencias de Android. |
| `data/remote` | Cliente Retrofit de `GET`/`POST /api/v1/siniestros` (`SiniestrosApi`) y su gateway (`RemoteSiniestrosGateway`). |
| `ui/validation` | `SiniestroFormValidation`: reglas del formulario (lugar, descripción ≥10, estimación decimal, fecha no futura, hora HH:MM). |
| `ui/siniestros` | `SiniestrosViewModel`. |
| `ui/screens/ClaimsScreen.kt` | Lista con estados de carga, error y vacío; etiquetas de origen (Automático/Manual) y estado; acción para reportar. |
| `ui/screens/ClaimFormScreen.kt` | Formulario de registro manual. |

Se entra desde el inicio con la acción **«Mis siniestros»**. Para la demo, siembra la póliza
paramétrica con `backend/sembrar_polizas.py` y dispara un evento con el proveedor de telemetría
(`uvicorn mocks.telemetry.main:app --port 8004`); el siniestro automático aparecerá en esta
pantalla. Reutiliza la `SesionAutenticada` del módulo de autenticación, igual que la billetera.

## 🪪 Registro desde Android (BPM-16)

El formulario recoge nombres, apellidos, tipo/número de documento, fecha de
nacimiento, correo, celular y contraseña. Solicita una selfie y envía los datos
a `POST /api/v1/auth/register` a través del mismo `AuthCoordinator` y gateway
remoto usados por autenticación. La app navega al inicio de sesión solo si el
backend responde con una cuenta creada y `kyc_validado=true`.

El flujo KYC incluido es **solo una demostración**: el mock responde
determinísticamente usando el número de documento, ignora el contenido de la
selfie y no hace reconocimiento facial ni prueba de vida. No debe utilizarse
para verificar identidades reales.

Para ejecutar la demo, desde `backend/` levanta el proveedor y el backend en
terminales separadas:

```powershell
uvicorn mocks.kyc.provider_a:app --reload --port 8001
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

En el emulador Android, la app usa `http://10.0.2.2:8000/`. Para un dispositivo
físico conectado por USB, puedes usar `adb reverse tcp:8000 tcp:8000` y compilar
con `-Psolventa.apiBaseUrl=http://127.0.0.1:8000/`.

---

## 🚀 Cómo Ejecutar en Local

### Requisitos previos
- **Android Studio** (Ladybug / Jellyfish o superior).
- **JDK 17**.
- **Android SDK** con soporte para `minSdk 24` y `compileSdk 37`.

### Pasos para ejecutar
1. Abrir la carpeta `android/` en Android Studio.
2. Sincronizar el proyecto con Gradle (**File > Sync Project with Gradle Files**).
3. Seleccionar un emulador Android (API 24+) o un dispositivo físico conectado con depuración USB.
4. Ejecutar la aplicación mediante el botón **Run (`app`)** o desde la terminal:

```bash
# Mismos chequeos que el pipeline
./gradlew lint testDebugUnitTest
```

En Windows PowerShell:

```powershell
.\gradlew.bat lint testDebugUnitTest
```

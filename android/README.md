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

---

## 🚀 Cómo Ejecutar en Local

### Requisitos previos
- **Android Studio** (Ladybug / Jellyfish o superior).
- **JDK 11** o superior.
- **Android SDK** con soporte para `minSdk 24` y `compileSdk 35`.

### Pasos para ejecutar
1. Abrir la carpeta `android/` en Android Studio.
2. Sincronizar el proyecto con Gradle (**File > Sync Project with Gradle Files**).
3. Seleccionar un emulador Android (API 24+) o un dispositivo físico conectado con depuración USB.
4. Ejecutar la aplicación mediante el botón **Run (`app`)** o desde la terminal:

```bash
# Compilar versión de depuración
./gradlew assembleDebug

# Ejecutar pruebas unitarias
./gradlew test
```
# Android

Aplicación móvil de Solventa, desarrollada con Kotlin y Jetpack Compose.

## Pruebas locales

Con JDK 17 y Android SDK instalados, ejecuta desde esta carpeta:

```bash
./gradlew lint testDebugUnitTest
```

En Windows PowerShell, usa:

```powershell
.\gradlew.bat lint testDebugUnitTest
```

Las pruebas unitarias verifican las condiciones para enviar los formularios de
inicio de sesión y registro, así como los identificadores de navegación.

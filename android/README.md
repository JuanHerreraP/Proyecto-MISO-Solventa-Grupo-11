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

# Evidencias de internacionalización y localización (web y Android)

Cada pantalla se muestra en **español de Colombia** (predeterminado) y en **inglés**, después de cambiar el
idioma desde el selector de la interfaz. Fecha: 23 de noviembre de 2026. Ver el diseño en
[docs/internacionalizacion.md](../../internacionalizacion.md).

- **Web:** la aplicación React corriendo contra el backend local (SQLite), con la clienta de prueba
  María Torres, una póliza de viaje emitida y un siniestro registrado. Capturas con Playwright
  (Chromium, 1366 × 820).
- **Android:** las pantallas reales de Compose con datos de ejemplo, dibujadas con Robolectric
  (gráficos nativos) en tamaño de teléfono (411 × 891 dp, xhdpi).

| Qué se verifica | Dónde se ve |
| --- | --- |
| Textos de la interfaz traducidos (menús, títulos, botones, estados, mensajes vacíos) | Todas las capturas |
| Selector de idioma visible y persistente | Web: ingreso, barra lateral y perfil · Android: Perfil → Idioma y moneda |
| Fechas según el idioma | Web pólizas: `22 de noviembre de 2026` / `November 22, 2026` · Android inicio: `15 oct 2026` / `Oct 15, 2026` |
| Moneda según el idioma | Web pólizas: `$ 20.000.000` / `COP 20,000,000` · Android pagos: `$1.245.000,50 COP` / `$1,245,000.50 COP` |
| `<html lang>` y contenido accesible por idioma | Web (verificado en `e2e/idioma/idioma.spec.ts`) |

Los nombres y estados que envía el backend (por ejemplo, "Seguro de viaje" o "CONFIRMADO") se muestran
tal como llegan, en español.

## Web

| Pantalla | Español | English |
| --- | --- | --- |
| Ingreso | ![Ingreso en español](web/1-es-01-ingreso.png) | ![Sign in in English](web/2-en-01-ingreso.png) |
| Inicio | ![Inicio en español](web/1-es-02-inicio.png) | ![Home in English](web/2-en-02-inicio.png) |
| Mis pólizas | ![Pólizas en español](web/1-es-03-polizas.png) | ![Policies in English](web/2-en-03-polizas.png) |
| Cotizar | ![Cotizar en español](web/1-es-04-cotizar.png) | ![Quote in English](web/2-en-04-cotizar.png) |
| Siniestros | ![Siniestros en español](web/1-es-05-siniestros.png) | ![Claims in English](web/2-en-05-siniestros.png) |
| Pagos | ![Pagos en español](web/1-es-06-pagos.png) | ![Payments in English](web/2-en-06-pagos.png) |
| Perfil e idioma | ![Perfil en español](web/1-es-07-perfil.png) | ![Profile in English](web/2-en-07-perfil.png) |

## Android

| Pantalla | Español | English |
| --- | --- | --- |
| Bienvenida | <img src="android/1-es-01-bienvenida.png" width="260" alt="Bienvenida en español"> | <img src="android/2-en-01-bienvenida.png" width="260" alt="Welcome in English"> |
| Inicio | <img src="android/1-es-02-inicio.png" width="260" alt="Inicio en español"> | <img src="android/2-en-02-inicio.png" width="260" alt="Home in English"> |
| Billetera | <img src="android/1-es-03-billetera.png" width="260" alt="Billetera en español"> | <img src="android/2-en-03-billetera.png" width="260" alt="Wallet in English"> |
| Pagos | <img src="android/1-es-04-pagos.png" width="260" alt="Pagos en español"> | <img src="android/2-en-04-pagos.png" width="260" alt="Payments in English"> |
| Perfil | <img src="android/1-es-05-perfil.png" width="260" alt="Perfil en español"> | <img src="android/2-en-05-perfil.png" width="260" alt="Profile in English"> |
| Selector de idioma | <img src="android/1-es-06-idioma.png" width="260" alt="Selector de idioma en español"> | <img src="android/2-en-06-idioma.png" width="260" alt="Language selector in English"> |

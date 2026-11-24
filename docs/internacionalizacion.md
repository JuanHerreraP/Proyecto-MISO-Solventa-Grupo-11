# Internacionalización y localización

Solventa se ofrece en **español de Colombia** (idioma predeterminado) y en **inglés**, en la web y en
la app Android. El usuario elige el idioma desde la interfaz; la elección se guarda en su dispositivo
y se aplica a los textos, a las fechas y a los montos.

## Resumen

| Aspecto | Web (React) | Android (Compose) |
| --- | --- | --- |
| Librería / mecanismo | `i18next` + `react-i18next` | Recursos de Android (`strings.xml`) |
| Catálogo español | `web/src/i18n/locales/es.ts` | `android/app/src/main/res/values/strings.xml` |
| Catálogo inglés | `web/src/i18n/locales/en.ts` | `android/app/src/main/res/values-en/strings.xml` |
| Textos externalizados | 881 | 499 |
| Dónde se cambia el idioma | Selector en ingreso/registro, barra lateral y Perfil | Perfil → Idioma y moneda |
| Persistencia | `localStorage` (`solventa.idioma`) | `SharedPreferences` (`solventa_idioma`) |
| Locale de formatos | `es-CO` / `en-US` con `Intl` | `es-CO` / `en-US` (`Idioma.locale()`, `Formatos`) |
| Atributo de idioma | `<html lang>` se actualiza al cambiar | Configuración de la actividad (`attachBaseContext`) |

## Web

- `web/src/i18n/index.ts` inicializa i18next, lee el idioma guardado (español si no hay ninguno),
  actualiza `<html lang>` y exporta `t`, `cambiarIdioma`, `idiomaActual` y `localeActual`.
- Las claves se agrupan por archivo: `loginPage.inicia_sesion`, `polizasPage.vigente`, etc.
- **Las claves están tipadas**: `i18next.d.ts` declara el catálogo en español como fuente, así que una
  clave inexistente no compila; `en.ts` usa el tipo `Catalogo<typeof es>`, así que si falta una
  traducción tampoco compila.
- Interpolación con nombre: `t("homePage.hola_nombre", { nombre })` → `"Hola, {{nombre}}"`.
- `App` usa `useTranslation()`: al cambiar el idioma se vuelve a pintar toda la interfaz sin recargar.
- Las constantes de módulo con etiquetas (estados, tipos de movimiento) usan getters, para que se
  traduzcan cada vez que se leen.
- Fechas, números y moneda usan `localeActual()` (`es-CO` → `$ 1.234.567`, `25/11/2026`;
  `en-US` → `COP 1,234,567`, `11/25/2026`).

### Agregar un texto en la web

1. Agregar la clave en `es.ts`, en el grupo del archivo que la usa.
2. Agregar la traducción con la misma clave en `en.ts` (el compilador avisa si falta).
3. Usar `t("grupo.clave")` en el componente.

## Android

- `i18n/Idioma.kt` carga el idioma guardado al iniciar la app (`SolventaApplication`) y lo aplica a la
  actividad en `MainActivity.attachBaseContext`.
- Los textos se leen con `tr(R.string.clave, argumentos…)`, que resuelve el recurso en el idioma
  activo. Funciona dentro y fuera de composables (mensajes de validación, textos para compartir).
- Al cambiar el idioma en Perfil, `Idioma.cambiar` guarda la elección y recrea la actividad.
- `Formatos` (dominio) cambia nombres de mes, orden de la fecha y separadores de miles y decimales;
  las pantallas formatean montos con `Idioma.locale()`.
- Los recursos con argumentos usan posiciones (`%1$s`, `%2$s`), igual en ambos idiomas.

### Agregar un texto en Android

1. Agregar `<string name="pantalla_clave">` en `values/strings.xml`.
2. Agregar la traducción con el mismo nombre en `values-en/strings.xml` (lint marca
   `MissingTranslation` si falta).
3. Usar `tr(R.string.pantalla_clave)` en el código.

## Pruebas

| Prueba | Qué verifica |
| --- | --- |
| `web/src/i18n/i18n.test.tsx` | Mismas claves y variables en ambos catálogos; español por defecto; cambio de idioma desde el selector, `<html lang>` y persistencia; formatos de fecha y moneda por idioma |
| `web/e2e/idioma/idioma.spec.ts` | Recorrido real: cambiar a inglés en el ingreso, iniciar sesión, ver menú, estados y montos en inglés, conservar la elección al recargar y volver al español |
| `android/.../i18n/IdiomaTest.kt` | Español por defecto; textos, fechas y moneda en inglés; persistencia; una pantalla pintada en inglés; traducción completa con los mismos argumentos |

Las pruebas existentes verifican los textos en español, el idioma predeterminado.

## Evidencias

Capturas de cada pantalla en español e inglés, web y Android:
[docs/evidencias/i18n](evidencias/i18n/README.md).

## Limitaciones conocidas

- Los mensajes y nombres que llegan del backend (por ejemplo, el nombre del ramo o el detalle de un
  error de la API) se muestran tal como los envía el servidor, en español.
- Los mensajes de error que generan los coordinadores del dominio en Android siguen en español.

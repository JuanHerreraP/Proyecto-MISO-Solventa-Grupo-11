# Accesibilidad

Solventa apunta a **WCAG 2.1 nivel AA** en la web y a las guías de accesibilidad de Android en la app.
La accesibilidad se verifica con pruebas automáticas en ambos canales y en los dos idiomas (español e
inglés), para que una regresión rompa la integración continua.

## Web

### Prueba automática

`web/e2e/accesibilidad/accesibilidad.spec.ts` recorre la aplicación con Playwright y analiza cada
pantalla con [axe-core](https://github.com/dequelabs/axe-core) usando las reglas `wcag2a`, `wcag2aa`,
`wcag21a` y `wcag21aa`. La prueba falla si encuentra cualquier violación.

| Pantallas | Idiomas |
| --- | --- |
| Ingreso, registro, inicio, mis pólizas, cotizar, mis cotizaciones, siniestros, reportar siniestro, pagos y perfil (10) | Español e inglés |

Las pantallas del cliente se revisan con datos reales: una clienta con póliza vigente y un siniestro
registrado. Además, la prueba verifica que `<html lang>` coincida con el idioma activo.

```bash
cd web
VITE_API_URL=http://localhost:8000 E2E_BACKEND_LOG=/tmp/backend.log npx playwright test e2e/accesibilidad
```

### Correcciones hechas

La primera ejecución encontró 24 elementos con problemas en 9 de las 10 pantallas (en español). Todos quedaron corregidos:

| Problema (regla de axe) | Dónde | Corrección |
| --- | --- | --- |
| Contraste insuficiente del texto secundario, 4,41:1 (`color-contrast`) | Subtítulos, ayudas y estados en todas las pantallas | `--solventa-muted` pasa de `#69758b` a `#5f6b80` (≥ 4,79:1 en todos los fondos) |
| Contraste del verde de "Vigente" y "Pagado", 3,92:1 | Inicio, pólizas, pagos, firma, endosos | Verde `#1b8a4a` → `#16753f` (5,14:1) |
| Contraste de íconos azules sobre fondo azul claro, 4,18:1 | Acciones rápidas, tarjetas del perfil | `#3867f2` → `#2f55d4` (5,46:1) |
| Tarjeta deshabilitada con opacidad 50 % (1,94:1) | Perfil → Notificaciones | Se distingue por color, sin bajar el contraste |
| Nombre accesible distinto del texto visible (`label-content-name-mismatch`) y fila de tabla con rol de botón | Historial reciente del inicio | La fila deja de ser botón; el tipo de movimiento es un `<button>` real cuyo nombre incluye el texto visible |

Evidencias antes y después (axe y Lighthouse, por pantalla e idioma): [docs/evidencias/accesibilidad](evidencias/accesibilidad/README.md).

### Prácticas ya presentes

- Etiquetas en todos los campos (`<label for>`), `aria-label` en botones de solo ícono y `alt` en imágenes.
- Íconos decorativos con `aria-hidden="true"`.
- Mensajes de error y de estado con `role="alert"` y `role="status"`, para que el lector los anuncie.
- Navegación principal con `<nav aria-label>` y `aria-current="page"` en la sección activa.
- Foco visible en controles personalizados.
- Idioma del documento (`<html lang>`) actualizado al cambiar de idioma.

## Android

### Prueba automática

`android/app/src/test/java/com/example/solventa/ui/accesibilidad/AccesibilidadTest.kt` (Robolectric)
pinta las pantallas principales en español e inglés y revisa su árbol de semántica, que es lo que
TalkBack anuncia:

- todo elemento táctil tiene un nombre (texto o `contentDescription`);
- todo campo de texto tiene una etiqueta;
- los elementos táctiles miden al menos 40 dp (los componentes de Material amplían su área de toque a
  48 dp con `minimumInteractiveComponentSize`).

Pantallas: bienvenida, ingreso biométrico, ingreso con credenciales, registro, inicio, billetera, pagos,
perfil y selector de idioma.

```bash
cd android
./gradlew testDebugUnitTest --tests "com.example.solventa.ui.accesibilidad.AccesibilidadTest"
```

### Prácticas ya presentes

- `contentDescription` en íconos con significado y `null` en los decorativos.
- `Role.Button` y `Role.RadioButton` en filas táctiles personalizadas; selector de idioma con
  `selectableGroup`.
- Componentes de Material 3 con área de toque mínima de 48 dp.
- Textos en `sp`, que respetan el tamaño de letra elegido en el teléfono.

## Revisión manual recomendada

Las pruebas automáticas detectan buena parte de los problemas, pero no todos. Antes de una entrega:

- **Web:** recorrer el flujo de compra solo con teclado (Tab, Enter, Espacio) y con un lector de
  pantalla (NVDA o VoiceOver); revisar con Lighthouse (pestaña *Lighthouse* de Chrome).
- **Android:** activar TalkBack y recorrer ingreso, inicio y billetera; aumentar el tamaño de letra del
  sistema al máximo y verificar que nada se corte.

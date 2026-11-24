/**
 * Internacionalización de la web (i18next + react-i18next).
 *
 * - Idiomas: español de Colombia (predeterminado) e inglés.
 * - El idioma elegido se guarda en localStorage y se refleja en <html lang>.
 * - Los formatos de fecha, número y moneda siguen el idioma activo (ver formato.ts).
 *
 * `t` se puede usar dentro y fuera de componentes. La raíz de la aplicación se suscribe
 * al cambio de idioma (ver main.tsx), así que toda la interfaz se vuelve a pintar al cambiarlo.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en";
import es from "./locales/es";

export const IDIOMAS = ["es", "en"] as const;
export type Idioma = (typeof IDIOMAS)[number];

export const IDIOMA_PREDETERMINADO: Idioma = "es";
const CLAVE_ALMACENAMIENTO = "solventa.idioma";

/** Locale BCP 47 usado por Intl para cada idioma de la interfaz. */
const LOCALES: Record<Idioma, string> = {
  es: "es-CO",
  en: "en-US",
};

function esIdioma(valor: unknown): valor is Idioma {
  return typeof valor === "string" && (IDIOMAS as readonly string[]).includes(valor);
}

function idiomaGuardado(): Idioma {
  try {
    const guardado = globalThis.localStorage?.getItem(CLAVE_ALMACENAMIENTO);
    if (esIdioma(guardado)) return guardado;
  } catch {
    // Almacenamiento no disponible (modo privado, pruebas): se usa el predeterminado.
  }
  return IDIOMA_PREDETERMINADO;
}

function reflejarEnDocumento(idioma: string): void {
  if (typeof document !== "undefined") document.documentElement.lang = idioma;
}

void i18n.use(initReactI18next).init({
  resources: {
    es: { translation: es },
    en: { translation: en },
  },
  lng: idiomaGuardado(),
  fallbackLng: IDIOMA_PREDETERMINADO,
  supportedLngs: [...IDIOMAS],
  interpolation: { escapeValue: false },
  initAsync: false,
  returnNull: false,
});

reflejarEnDocumento(i18n.language);

i18n.on("languageChanged", (idioma) => {
  reflejarEnDocumento(idioma);
  try {
    globalThis.localStorage?.setItem(CLAVE_ALMACENAMIENTO, idioma);
  } catch {
    // Si no se puede guardar, el cambio aplica solo a esta sesión.
  }
});

/** Traduce una clave del catálogo; equivale a `useTranslation().t`. */
export const t = i18n.t.bind(i18n);

export function idiomaActual(): Idioma {
  return esIdioma(i18n.language) ? i18n.language : IDIOMA_PREDETERMINADO;
}

/** Locale para Intl (fechas, números y moneda) según el idioma activo. */
export function localeActual(): string {
  return LOCALES[idiomaActual()];
}

export function cambiarIdioma(idioma: Idioma): Promise<unknown> {
  return i18n.changeLanguage(idioma);
}

export default i18n;

import "i18next";

import type es from "./locales/es";

/** Tipa las claves de `t()` con el catálogo en español: una clave inexistente no compila. */
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation";
    resources: {
      translation: typeof es;
    };
    returnNull: false;
  }
}

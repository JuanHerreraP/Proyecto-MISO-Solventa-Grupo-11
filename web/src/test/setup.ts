import "@testing-library/jest-dom/vitest";

import {
  cleanup,
} from "@testing-library/react";

import {
  afterEach,
  beforeEach,
} from "vitest";

import i18n from "../i18n";

// Las pruebas verifican los textos en español, el idioma predeterminado de la aplicación.
beforeEach(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
});

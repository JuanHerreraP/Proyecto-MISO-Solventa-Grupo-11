import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useTranslation } from "react-i18next";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import i18n, { cambiarIdioma, idiomaActual, localeActual, t } from ".";
import LoginPage from "../pages/LoginPage";
import en from "./locales/en";
import es from "./locales/es";

vi.mock("../services/auth.service", () => ({ login: vi.fn(), register: vi.fn() }));

type Catalogo = { [clave: string]: string | Catalogo };

function claves(catalogo: Catalogo, prefijo = ""): string[] {
  return Object.entries(catalogo).flatMap(([clave, valor]) =>
    typeof valor === "string" ? [`${prefijo}${clave}`] : claves(valor, `${prefijo}${clave}.`),
  );
}

function valor(catalogo: Catalogo, ruta: string): string {
  return ruta.split(".").reduce<string | Catalogo>((nodo, parte) => (nodo as Catalogo)[parte], catalogo) as string;
}

/** Igual que App: se suscribe al idioma y vuelve a pintar la página al cambiarlo. */
function Raiz() {
  useTranslation();
  return (
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

function renderLogin() {
  return render(<Raiz />);
}

describe("internacionalización", () => {
  it("el catálogo en inglés tiene las mismas claves y variables que el de español", () => {
    const clavesEs = claves(es);
    expect(claves(en)).toEqual(clavesEs);
    for (const clave of clavesEs) {
      const variables = (texto: string) => (texto.match(/\{\{\w+\}\}/g) ?? []).sort();
      expect(variables(valor(en, clave)), clave).toEqual(variables(valor(es, clave)));
      expect(valor(en, clave).trim(), clave).not.toBe("");
    }
  });

  it("usa español de Colombia por defecto", () => {
    expect(idiomaActual()).toBe("es");
    expect(localeActual()).toBe("es-CO");
    expect(t("loginPage.inicia_sesion")).toBe("Inicia sesión");
  });

  it("cambia la interfaz al inglés desde el selector y recuerda la elección", async () => {
    renderLogin();
    expect(screen.getByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByRole("combobox", { name: /Idioma/ }), "en");

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /Language/ })).toHaveValue("en");
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem("solventa.idioma")).toBe("en");
  });

  it("formatea fechas y moneda según el idioma activo", async () => {
    const monto = (valor: number) =>
      new Intl.NumberFormat(localeActual(), { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(valor);
    const fecha = (iso: string) => new Date(iso).toLocaleDateString(localeActual(), { timeZone: "UTC" });

    expect(monto(1234567)).toMatch(/1\.234\.567/);
    expect(fecha("2026-11-25T12:00:00Z")).toBe("25/11/2026");

    await cambiarIdioma("en");
    expect(localeActual()).toBe("en-US");
    expect(monto(1234567)).toMatch(/1,234,567/);
    expect(fecha("2026-11-25T12:00:00Z")).toBe("11/25/2026");
    await i18n.changeLanguage("es");
  });
});

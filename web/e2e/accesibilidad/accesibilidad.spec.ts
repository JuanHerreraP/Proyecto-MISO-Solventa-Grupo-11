import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { SolventaApi, uniqueUser } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

/** Criterios WCAG 2.1 niveles A y AA que revisa axe-core. */
const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

const PUBLICAS = ["/login", "/registro"];
const PRIVADAS = ["/home", "/polizas", "/cotizar", "/cotizaciones", "/siniestros", "/siniestros/nuevo", "/pagos", "/perfil"];

async function revisar(page: Page, ruta: string) {
  await page.goto(ruta);
  await expect(page.locator("main")).toBeVisible();
  // Espera a que la página termine de cargar sus datos (sin indicadores de carga).
  await expect(page.getByRole("status").filter({ hasText: /Cargando|Loading/ })).toHaveCount(0);
  const resultado = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  const resumen = resultado.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
  expect(resumen, `Violaciones de accesibilidad en ${ruta}`).toEqual([]);
}

for (const idioma of ["es", "en"] as const) {
  test.describe(`accesibilidad WCAG 2.1 AA (${idioma})`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((valor) => localStorage.setItem("solventa.idioma", valor), idioma);
    });

    for (const ruta of PUBLICAS) {
      test(`sin violaciones en ${ruta}`, async ({ page }) => {
        await revisar(page, ruta);
        await expect(page.locator("html")).toHaveAttribute("lang", idioma);
      });
    }

    test("sin violaciones en las pantallas del cliente", async ({ page, request }) => {
      // Clienta con póliza vigente y un siniestro, para que las pantallas muestren datos reales.
      const api = new SolventaApi(request);
      const cliente = await api.registerClient({ ...uniqueUser(), nombre: "María", apellido: "Torres" });
      const { policyId } = await api.issuePolicy(cliente, undefined, api.travelRisk(-1, 20));
      await api.registerClaim(cliente, policyId);

      await loginUi(page, cliente);
      for (const ruta of PRIVADAS) await revisar(page, ruta);
    });
  });
}

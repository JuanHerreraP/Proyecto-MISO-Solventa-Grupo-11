import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

/** Ayer (UTC): con hoy y una hora fija el evento queda en el futuro antes de esa hora. */
const ayer = () => new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);

test("registra un siniestro y lo consulta en el listado", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client, undefined, api.travelRisk(-1, 10));
  await loginUi(page, client);

  await page.goto("/siniestros/nuevo");
  await page.locator("input[name='poliza']").first().check();
  await page.getByLabel("Fecha del evento").fill(ayer());
  await page.getByLabel("Hora del evento").fill("10:30");
  await page.getByLabel("Lugar").fill("Aeropuerto Internacional El Dorado");
  await page.getByLabel("Descripción detallada").fill("Equipaje extraviado durante el trayecto contratado.");
  await page.getByLabel("Estimación preliminar de daños (COP)").fill("850000");
  await page.getByRole("button", { name: "Registrar siniestro" }).click();
  await expect(page.getByRole("heading", { name: "Siniestro registrado" })).toBeVisible();
  const claimId = await page.getByText("Número de siniestro").locator("..").locator("dd").textContent();

  await page.getByRole("button", { name: "Ver mis siniestros" }).click();
  await expect(page.getByRole("heading", { name: "Mis siniestros" })).toBeVisible();
  const claim = page.locator("article.cotizacion-item").first();
  await claim.locator("button.cotizacion-cabecera").click();
  if (claimId) await expect(claim.getByText(claimId.trim(), { exact: true })).toBeVisible();
  await expect(claim.getByText("Equipaje extraviado durante el trayecto contratado.")).toBeVisible();
});

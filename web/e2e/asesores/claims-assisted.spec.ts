import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

/** Ayer (UTC): con hoy y una hora fija el evento queda en el futuro antes de esa hora. */
const ayer = () => new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);

test("el asesor registra un siniestro para un cliente asociado", async ({ page, request }) => {
  test.skip(
    !process.env.E2E_ADMIN_EMAIL || !process.env.E2E_ADMIN_PASSWORD,
    "Requiere E2E_ADMIN_EMAIL y E2E_ADMIN_PASSWORD.",
  );
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client, undefined, api.travelRisk(-1, 10));
  const advisor = await api.createAdvisor();
  const advisorToken = await api.login(advisor);
  await api.associateClient(advisorToken, client);
  await loginUi(page, advisor);

  await page.goto("/siniestros/nuevo");
  await page.getByLabel("Cliente que atiendes").selectOption(client.id);
  await page.locator("input[name='poliza']").first().check();
  await page.getByLabel("Fecha del evento").fill(ayer());
  await page.getByLabel("Hora del evento").fill("11:00");
  await page.getByLabel("Lugar").fill("Aeropuerto Internacional El Dorado");
  await page.getByLabel("Descripción detallada").fill("El asesor registra la pérdida del equipaje del cliente.");
  await page.getByLabel("Estimación preliminar de daños (COP)").fill("900000");
  await page.getByRole("button", { name: "Registrar siniestro" }).click();

  await expect(page.getByRole("heading", { name: "Siniestro registrado" })).toBeVisible();
  await expect(page.getByText("La reclamación del cliente fue registrada correctamente.")).toBeVisible();
});

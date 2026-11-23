import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { cancelVisiblePolicy, loginUi } from "../helpers/ui.js";

test.describe.configure({ mode: "serial" });

test("el cliente consulta la prorrata y cancela su póliza", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client);

  await loginUi(page, client);
  await page.goto("/polizas");
  await cancelVisiblePolicy(page);
});

test("el asesor cancela una póliza de venta asistida de su cliente", async ({ page, request }) => {
  test.skip(
    !process.env.E2E_ADMIN_EMAIL || !process.env.E2E_ADMIN_PASSWORD,
    "Requiere E2E_ADMIN_EMAIL y E2E_ADMIN_PASSWORD.",
  );
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  const advisor = await api.createAdvisor();
  const advisorToken = await api.login(advisor);
  await api.associateClient(advisorToken, client);
  await api.issuePolicy(client, advisorToken);

  await loginUi(page, advisor);
  await page.goto("/polizas");
  const clientSelect = page.getByLabel("Selecciona un cliente");
  await clientSelect.selectOption(client.id);
  await expect(clientSelect).toHaveValue(client.id);
  const policy = page.locator("article.cotizacion-item").first();
  await policy.locator("button.cotizacion-cabecera").click();
  await policy.getByRole("button", { name: "Cancelar póliza" }).click();
  await expect(page.getByText(/Estás gestionando esta cancelación como asesor/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Liquidación estimada" })).toBeVisible();
  await page.getByLabel("Selecciona un motivo").selectOption("PRECIO_ALTO");
  await page.getByLabel("Confirmo que quiero cancelar esta póliza de forma definitiva.").check();
  await page.getByRole("button", { name: "Confirmar cancelación" }).click();
  await expect(page.getByRole("heading", { name: "Póliza cancelada" })).toBeVisible();
});

import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

test.beforeEach(() => {
  test.skip(
    !process.env.E2E_ADMIN_EMAIL || !process.env.E2E_ADMIN_PASSWORD,
    "Requiere E2E_ADMIN_EMAIL y E2E_ADMIN_PASSWORD.",
  );
});

test("el asesor asocia un cliente desde su inicio", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  const advisor = await api.createAdvisor();
  await loginUi(page, advisor);

  await page.getByLabel("Correo del cliente").fill(client.email);
  await page.getByRole("button", { name: "Asociar cliente" }).click();
  await expect(page.getByRole("status")).toContainText(`Cliente ${client.nombre} ${client.apellido} asociado`);
  await expect(page.getByText(client.email, { exact: true })).toBeVisible();
});

test("el asesor consulta las pólizas de un cliente asociado", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client);
  const advisor = await api.createAdvisor();
  const advisorToken = await api.login(advisor);
  await api.associateClient(advisorToken, client);
  await loginUi(page, advisor);

  await page.goto("/polizas");
  await page.getByLabel("Selecciona un cliente").selectOption(client.id);
  await expect(page.locator("article.cotizacion-item").first()).toBeVisible();
  await expect(page.getByText("Vigente", { exact: true })).toBeVisible();
});

test("el asesor no cancela una póliza que no originó", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client);
  const advisor = await api.createAdvisor();
  const advisorToken = await api.login(advisor);
  await api.associateClient(advisorToken, client);
  await loginUi(page, advisor);

  await page.goto("/polizas");
  await page.getByLabel("Selecciona un cliente").selectOption(client.id);
  const policy = page.locator("article.cotizacion-item").first();
  await policy.locator("button.cotizacion-cabecera").click();
  await policy.getByRole("button", { name: "Cancelar póliza" }).click();
  await expect(page.getByRole("alert")).toContainText("solo puede cancelar pólizas de sus ventas asistidas");
  await expect(page.getByRole("button", { name: "Confirmar cancelación" })).not.toBeVisible();
});

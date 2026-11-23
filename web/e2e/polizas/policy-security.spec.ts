import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

test("descarga el PDF de una póliza emitida", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client);
  await loginUi(page, client);
  await page.goto("/polizas");

  const policy = page.locator("article.cotizacion-item").first();
  await policy.locator("button.cotizacion-cabecera").click();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    policy.getByRole("button", { name: "Descargar póliza (PDF)" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
  expect(await download.failure()).toBeNull();
});

test("impide consultar una póliza perteneciente a otro cliente", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const owner = await api.registerClient();
  const stranger = await api.registerClient();
  const { policyId } = await api.issuePolicy(owner);
  await loginUi(page, stranger);

  await page.goto(`/polizas/${encodeURIComponent(policyId)}/cancelar`);
  await expect(page.getByRole("alert")).toContainText("La póliza no existe");
  await expect(page.getByRole("heading", { name: "Liquidación estimada" })).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar cancelación" })).not.toBeVisible();
});

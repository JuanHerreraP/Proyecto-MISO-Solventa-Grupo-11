import { expect, test, type Page } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

async function fillCard(page: Page, number: string): Promise<void> {
  await page.getByLabel("Número de tarjeta").fill(number);
  await page.getByLabel("Vencimiento (MM/AA)").fill("1229");
  await page.getByLabel("CVV").fill("123");
}

test("reintenta con éxito después de un pago rechazado", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  const quoteId = await api.createQuote(client);
  await loginUi(page, client);

  await page.goto(`/cotizar?cotizacion=${encodeURIComponent(quoteId)}`);
  await fillCard(page, "4111111111111110");
  await page.getByRole("button", { name: "Pagar prima" }).click();
  await expect(page.getByText("Pago rechazado", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Reintentar pago" }).click();
  await fillCard(page, "4111111111111111");
  await page.getByRole("button", { name: "Pagar prima" }).click();
  await expect(page.getByText("Pago aprobado", { exact: true })).toBeVisible();
});

import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

test("muestra una cotización vigente con su referencia y opción de pago", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  const quoteId = await api.createQuote(client);
  await loginUi(page, client);
  await page.goto("/cotizaciones");

  const quote = page.locator("article.cotizacion-item").first();
  await expect(quote).toBeVisible();
  await quote.locator("button.cotizacion-cabecera").click();
  await expect(quote.getByText(quoteId, { exact: true })).toBeVisible();
  await expect(quote.getByRole("button", { name: "Pagar" })).toBeVisible();
});

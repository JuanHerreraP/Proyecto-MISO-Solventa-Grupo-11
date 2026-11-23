import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";

test("cambia la interfaz a inglés, formatea según el idioma y conserva la elección", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client);

  await page.goto("/login");
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await expect(page.getByRole("heading", { name: "Inicia sesión" })).toBeVisible();

  await page.getByRole("combobox", { name: /Idioma/ }).selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

  await page.getByLabel("Email").fill(client.email);
  await page.getByLabel("Password").fill(client.password);
  await page.getByRole("button", { name: "Sign in →" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("heading", { name: `Hello, ${client.nombre}` })).toBeVisible();
  const menu = page.getByRole("navigation", { name: "Main" });
  await expect(menu.getByRole("button", { name: "My policies" })).toBeVisible();

  await menu.getByRole("button", { name: "My policies" }).click();
  const poliza = page.locator("article.cotizacion-item").first();
  await expect(poliza.getByText("Active", { exact: true })).toBeVisible();
  await poliza.locator("button.cotizacion-cabecera").click();
  // Montos con el formato de en-US: separador de miles con coma.
  await expect(poliza.getByText(/\d{1,3}(,\d{3})+/).first()).toBeVisible();

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("navigation", { name: "Main" }).getByRole("button", { name: "My policies" })).toBeVisible();

  await page.getByRole("combobox", { name: /Language/ }).selectOption("es");
  await expect(page.getByRole("navigation", { name: "Principal" }).getByRole("button", { name: "Mis pólizas" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
});

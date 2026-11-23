import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

test("rechaza credenciales inválidas sin crear una sesión", async ({ page, request }) => {
  const client = await new SolventaApi(request).registerClient();
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill(client.email);
  await page.getByLabel("Contraseña").fill("ContraseñaIncorrecta-123");
  await page.getByRole("button", { name: "Iniciar sesión →" }).click();

  await expect(page.getByRole("alert")).toContainText("correo electrónico o la contraseña son incorrectos");
  await expect(page).toHaveURL(/\/login$/);
});

test("impide que un cliente acceda a la administración de asesores", async ({ page, request }) => {
  const client = await new SolventaApi(request).registerClient();
  await loginUi(page, client);
  await page.goto("/admin/asesores/nuevo");

  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("alert")).toContainText("No tienes permiso");
});

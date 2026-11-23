import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

test("restaura y renueva la sesión al recargar la aplicación", async ({ page, request }) => {
  const client = await new SolventaApi(request).registerClient();
  await loginUi(page, client);
  await page.goto("/perfil");
  await expect(page.getByRole("heading", { name: "Perfil y preferencias" })).toBeVisible();

  const [refreshResponse] = await Promise.all([
    page.waitForResponse((response) =>
      response.url().includes("/api/v1/auth/web/refresh") && response.request().method() === "POST"
    ),
    page.reload(),
  ]);
  expect(refreshResponse.ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/perfil$/);
  await expect(page.getByRole("heading", { name: "Perfil y preferencias" })).toBeVisible();
});

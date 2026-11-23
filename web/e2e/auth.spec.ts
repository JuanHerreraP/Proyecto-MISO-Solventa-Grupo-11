import { expect, test } from "@playwright/test";
import { SolventaApi } from "./helpers/api.js";
import { loginUi } from "./helpers/ui.js";

test("protege rutas, inicia sesión, muestra el perfil y cierra sesión", async ({ page, request }) => {
  const user = await new SolventaApi(request).registerClient();

  await page.goto("/perfil");
  await expect(page).toHaveURL(/\/login$/);

  await loginUi(page, user);
  await page.goto("/perfil");
  await expect(page.getByRole("heading", { name: "Perfil y preferencias" })).toBeVisible();
  const identity = page.getByRole("region", { name: "Identidad de la cuenta" });
  await expect(identity.getByText(`${user.nombre} ${user.apellido}`, { exact: true })).toBeVisible();
  await expect(identity.getByText(user.email, { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/perfil");
  await expect(page).toHaveURL(/\/login$/);
});

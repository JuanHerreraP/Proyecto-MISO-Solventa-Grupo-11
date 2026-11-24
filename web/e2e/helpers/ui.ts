import { expect, type Page } from "@playwright/test";
import type { TestUser } from "./api.js";

export async function loginUi(page: Page, user: Pick<TestUser, "email" | "password">): Promise<void> {
  await page.goto("/login");
  // Funciona en español e inglés (el idioma puede venir guardado de antes).
  await page.getByLabel(/^(Correo electrónico|Email)$/).fill(user.email);
  await page.getByLabel(/^(Contraseña|Password)$/).fill(user.password);
  await page.getByRole("button", { name: /^(Iniciar sesión|Sign in) →$/ }).click();
  await expect(page).toHaveURL(/\/home$/);
}

export async function cancelVisiblePolicy(page: Page): Promise<void> {
  const policy = page.locator("article.cotizacion-item").first();
  await expect(policy).toBeVisible();
  await policy.locator("button.cotizacion-cabecera").click();
  await policy.getByRole("button", { name: "Cancelar póliza" }).click();
  await expect(page.getByRole("heading", { name: "Liquidación estimada" })).toBeVisible();
  await expect(page.getByText("Saldo estimado a devolver", { exact: true })).toBeVisible();
  await page.getByLabel("Selecciona un motivo").selectOption("PRECIO_ALTO");
  await page.getByLabel("Confirmo que quiero cancelar esta póliza de forma definitiva.").check();
  await page.getByRole("button", { name: "Confirmar cancelación" }).click();
  await expect(page.getByRole("heading", { name: "Póliza cancelada" })).toBeVisible();
}

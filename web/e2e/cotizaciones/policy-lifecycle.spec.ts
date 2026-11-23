import { expect, test } from "@playwright/test";
import { SolventaApi, readOtp } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

test("cotiza, paga, firma y muestra la póliza emitida", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const user = await api.registerClient();
  await loginUi(page, user);

  await page.goto("/cotizar");
  await page.getByRole("button", { name: /Seguro de viaje/ }).click();
  const risk = api.travelRisk();
  await page.getByLabel("Destino").fill(String(risk.destino));
  await page.getByLabel("Fecha de inicio").fill(String(risk.fecha_inicio));
  await page.getByLabel("Fecha de finalización").fill(String(risk.fecha_fin));
  await page.getByLabel("Número de viajeros").fill(String(risk.numero_viajeros));
  await page.getByLabel(/Valor asegurado/).fill(String(risk.valor_asegurado));
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Aceptar y continuar" }).click();

  await page.getByLabel("Número de tarjeta").fill("4111111111111111");
  await page.getByLabel("Vencimiento (MM/AA)").fill("1229");
  await page.getByLabel("CVV").fill("123");
  await page.getByRole("button", { name: "Pagar prima" }).click();
  await expect(page.getByText("Pago aprobado", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Firmar contrato" }).click();

  await page.getByLabel(/Leí el contrato y autorizo/).check();
  await page.getByLabel("Correo electrónico").check();
  await page.getByRole("button", { name: "Enviar código" }).click();
  await expect(page.getByLabel("Código de verificación")).toBeVisible();

  const contractResponse = await request.get(
    `${process.env.E2E_API_URL ?? process.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1/firmas/${encodeURIComponent(page.url().split("/").pop() ?? "")}`,
    { headers: { Authorization: `Bearer ${await api.login(user)}` } },
  );
  expect(contractResponse.ok()).toBeTruthy();
  const signatureProcess = await contractResponse.json() as { firma_id: string };
  const otp = readOtp(signatureProcess.firma_id);
  await page.getByLabel("Código de verificación").fill(otp);
  await page.getByRole("button", { name: "Firmar contrato" }).click();

  await expect(page.getByLabel("Póliza emitida")).toBeVisible();
  await page.getByRole("button", { name: "Finalizar e ir a mis pólizas" }).click();
  await expect(page).toHaveURL(/\/polizas$/);
  await expect(page.locator("article.cotizacion-item")).toHaveCount(1);
  await expect(page.getByText("Vigente", { exact: true })).toBeVisible();
});

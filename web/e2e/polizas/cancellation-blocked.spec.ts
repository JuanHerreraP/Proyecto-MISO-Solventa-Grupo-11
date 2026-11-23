import { expect, test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { loginUi } from "../helpers/ui.js";

test("bloquea la cancelación cuando existe un siniestro en trámite", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  const { policyId } = await api.issuePolicy(client, undefined, api.travelRisk(-1, 10));
  await api.registerClaim(client, policyId);
  await loginUi(page, client);

  await page.goto(`/polizas/${encodeURIComponent(policyId)}/cancelar`);
  await expect(page.getByRole("heading", { name: "Esta póliza no se puede cancelar" })).toBeVisible();
  await expect(page.getByText(/siniestro.*trámite/i)).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar cancelación" })).not.toBeVisible();
});

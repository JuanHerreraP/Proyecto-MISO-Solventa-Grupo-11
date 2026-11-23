import { test } from "@playwright/test";
import { SolventaApi } from "../helpers/api.js";
import { cancelVisiblePolicy, loginUi } from "../helpers/ui.js";

test("el cliente consulta la prorrata y cancela su póliza", async ({ page, request }) => {
  const api = new SolventaApi(request);
  const client = await api.registerClient();
  await api.issuePolicy(client);

  await loginUi(page, client);
  await page.goto("/polizas");
  await cancelVisiblePolicy(page);
});

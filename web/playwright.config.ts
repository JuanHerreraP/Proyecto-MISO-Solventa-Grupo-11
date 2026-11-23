import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import process from "node:process";

if (existsSync(".env.e2e.local")) process.loadEnvFile(".env.e2e.local");

const externalBaseUrl = process.env.E2E_BASE_URL;
const baseURL = externalBaseUrl ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./e2e/evidencias/artifacts",
  timeout: 60_000,
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never", outputFolder: "./e2e/evidencias/report" }]]
    : [["list"], ["html", { open: "never", outputFolder: "./e2e/evidencias/report" }]],
  use: {
    baseURL,
    screenshot: "on",
    trace: "off",
    video: "off",
  },
  webServer: externalBaseUrl
    ? undefined
    : {
        command: "npm run dev -- --host 127.0.0.1",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

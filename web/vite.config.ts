import { configDefaults, defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [
    react(),
  ],

  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    // Los recorridos Playwright se ejecutan con `npm run test:e2e`, no con Vitest.
    exclude: [...configDefaults.exclude, "e2e/**"],

    coverage: {
      provider: "v8",

      reporter: [
        "text",
        "html",
      ],

      include: [
        "src/**/*.{ts,tsx}",
      ],

      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/types/**",
        "src/main.tsx",
        "src/**/*.css",
      ],
    },
  },
});

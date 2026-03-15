import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "node e2e/start-backend.mjs",
      cwd: __dirname,
      url: "http://127.0.0.1:8100/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "node e2e/start-frontend.mjs",
      cwd: __dirname,
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});

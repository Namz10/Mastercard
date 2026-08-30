import { defineConfig } from "@playwright/test";

const BRAVE = "/usr/bin/brave-browser";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1920, height: 1080 },
    browserName: "chromium",
    executablePath: BRAVE,
    launchOptions: {
      executablePath: BRAVE,
    },
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5173",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
  projects: [
    {
      name: "brave",
      use: {
        viewport: { width: 1920, height: 1080 },
        executablePath: BRAVE,
      },
    },
  ],
});

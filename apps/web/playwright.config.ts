import { defineConfig, devices } from "@playwright/test";

/**
 * 前端 E2E 演示测试（Playwright）。
 *
 * 前提：后端已在本机 8000 端口运行（推荐 MockProvider + fallback renderer）：
 *   LLM_PROVIDER=mock AUDIO_RENDERER=fallback uvicorn services.api.main:app --port 8000
 *
 * webServer 自动启动 Vite dev server（5173，/api 代理到 8000）。
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

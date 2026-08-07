import { expect, test } from "@playwright/test";

/**
 * T33.1 路由 smoke：三路由结构 + NotFound + 刷新恢复。
 * 需要本机 8000 端口运行 MockProvider 后端。
 */

test("/ 自动跳转 /create", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/create$/);
  await expect(page.getByRole("heading", { name: "生成控制台" })).toBeVisible();
});

test("/create 可渲染生成能力", async ({ page }) => {
  await page.goto("/create");
  await expect(page.getByRole("heading", { name: "生成控制台" })).toBeVisible();
  const promptBox = page.getByRole("textbox").first();
  await expect(promptBox).toBeVisible();
});

test("/projects 可渲染工程库壳", async ({ page }) => {
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "工程库" })).toBeVisible();
});

test("/projects/:songId 从 URL 取得 songId 并加载工作台", async ({ page }) => {
  // 先通过创建页生成一个工程，获得 song_id
  await page.goto("/create");
  const promptBox = page.getByRole("textbox").first();
  await promptBox.fill("生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调");
  await page.getByRole("button", { name: "生成 MusicSpec" }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+/, { timeout: 60_000 });

  // 工作台应可见（WorkspaceHeader）
  await expect(page.getByRole("heading", { name: "AI Music Studio" })).toBeVisible({ timeout: 30_000 });
});

test("/projects/:songId 刷新后 songId 不丢失", async ({ page }) => {
  await page.goto("/create");
  const promptBox = page.getByRole("textbox").first();
  await promptBox.fill("生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调");
  await page.getByRole("button", { name: "生成 MusicSpec" }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+/, { timeout: 60_000 });
  const url = page.url();

  // 直接刷新：URL 不变，工作台仍加载
  await page.reload();
  await expect(page).toHaveURL(url);
  await expect(page.getByRole("heading", { name: "AI Music Studio" })).toBeVisible({ timeout: 30_000 });
});

test("未知路径显示 NotFoundPage", async ({ page }) => {
  await page.goto("/definitely-not-a-page");
  await expect(page.getByText("页面不存在")).toBeVisible();
});

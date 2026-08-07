import { expect, test } from "@playwright/test";

/**
 * T33.1 路由 smoke：三路由结构 + NotFound + 刷新恢复。
 * 需要本机 8000 端口运行 MockProvider 后端。
 */

test("/ 自动跳转 /create", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/create$/);
  await expect(page.getByRole("heading", { name: "创作新音乐" })).toBeVisible();
});

test("/create 可渲染生成能力", async ({ page }) => {
  await page.goto("/create");
  await expect(page.getByRole("heading", { name: "创作新音乐" })).toBeVisible();
  const promptBox = page.getByRole("textbox").first();
  await expect(promptBox).toBeVisible();
});

test("/projects 可渲染工程库壳", async ({ page }) => {
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "工程库" })).toBeVisible();
});

async function createProjectViaApi(): Promise<string> {
  const response = await fetch("http://127.0.0.1:8000/api/v1/songs/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: "生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调" }),
  });
  if (!response.ok) throw new Error(`create project failed: ${response.status}`);
  const data = (await response.json()) as { song_id: string };
  return data.song_id;
}

test("/projects/:songId 从 URL 取得 songId 并加载工作台", async ({ page }) => {
  const songId = await createProjectViaApi();
  await page.goto(`/projects/${songId}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${songId}`));
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });
});

test("/projects/:songId 刷新后 songId 不丢失", async ({ page }) => {
  const songId = await createProjectViaApi();
  const url = `/projects/${songId}`;
  await page.goto(url);
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });

  // 直接刷新：URL 不变，工作台仍加载
  await page.reload();
  await expect(page).toHaveURL(new RegExp(`/projects/${songId}`));
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });
});

test("未知路径显示 NotFoundPage", async ({ page }) => {
  await page.goto("/definitely-not-a-page");
  await expect(page.getByText("页面不存在")).toBeVisible();
});

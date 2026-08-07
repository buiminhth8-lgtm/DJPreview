import { expect, test } from "@playwright/test";

/**
 * Flow B：/projects → 打开工程 → 刷新恢复 → 编辑 → 版本 → 导出入口。
 * Flow C 子集：删除二次确认（Cancel 不删 / Confirm 删除后回 /projects）。
 * 需要本机 8000 端口运行 MockProvider 后端。
 */

async function createProjectViaApi(prompt = "生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调"): Promise<string> {
  const response = await fetch("http://127.0.0.1:8000/api/v1/songs/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!response.ok) throw new Error(`create project failed: ${response.status}`);
  const data = (await response.json()) as { song_id: string };
  return data.song_id;
}

test("flow b: library open workspace refresh edit version export", async ({ page }) => {
  const songId = await createProjectViaApi();
  const editRequests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) {
      editRequests.push(`${r.method()} ${r.url()}`);
    }
  });
  let editResponseStatus = -1;
  page.on("response", (r) => {
    const path = r.url().replace("http://127.0.0.1:49152", "");
    if (r.request().method() !== "GET" || path.includes("/edit")) {
      console.log("RESP", r.status(), r.request().method(), path);
    }
    if (r.status() >= 400) {
      console.log("HTTPERR", r.status(), r.request().method(), path);
    }
  });
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(`PAGEERROR: ${err.message}`));

  // 1. /projects 列表可见，且包含刚创建的工程
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "工程库" })).toBeVisible();
  const card = page.locator(`[data-song-id="${songId}"]`);
  await expect(card).toBeVisible({ timeout: 15_000 });

  // 2. 打开工程 → URL /projects/:songId
  await card.click();
  await expect(page).toHaveURL(new RegExp(`/projects/${songId}`));
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });

  // 3. 浏览器刷新后工程恢复
  await page.reload();
  await expect(page).toHaveURL(new RegExp(`/projects/${songId}`));
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });

  // 4. 自然语言编辑 → 版本应创建 v2（编辑后版本面板自动刷新）
  const editBox = page.getByPlaceholder(/例如：让副歌更宏大/).first();
  await editBox.fill("整首更快一点");
  const applyButton = page.getByRole("button", { name: "应用修改" }).first();
  await expect(applyButton).toBeEnabled({ timeout: 10_000 });
  console.log("apply button count:", await page.getByRole("button", { name: "应用修改" }).count());
  console.log("apply disabled:", await applyButton.isDisabled());
  await applyButton.click();
  await page.waitForTimeout(3000);
  console.log("edit requests after click:", JSON.stringify(editRequests.filter((u) => u.includes("/edit"))));
  console.log("console errors:", JSON.stringify(consoleErrors));
  // 版本面板点击“刷新版本”后应出现 v2（编辑已创建新版本）
  await page.getByRole("button", { name: "刷新版本" }).first().click();
  const versionPanelText = page.locator(".workspace-versions").first();
  await expect(versionPanelText).toContainText("v2", { timeout: 30_000 });

  // 5. 导出入口存在（工程导入导出面板）
  await expect(page.getByRole("button", { name: "导出工程" }).first()).toBeVisible({ timeout: 15_000 });
});

test("flow c delete: cancel keeps project, confirm deletes and navigates", async ({ page }) => {
  const songId = await createProjectViaApi("生成一首轻快的流行歌曲");
  await page.goto(`/projects/${songId}`);
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });

  // 1. 打开删除对话框 → Cancel → 不删除
  await page.getByRole("button", { name: "删除当前工程" }).click();
  await expect(page.getByText("删除工程？")).toBeVisible();
  await page.getByRole("button", { name: "取消" }).click();
  await expect(page.getByText("删除工程？")).toBeHidden();

  // 确认工程仍在（工作台仍可访问）
  await expect(page.getByText(/song_id：/).first()).toBeVisible();

  // 2. 再次删除 → Confirm → 回到 /projects
  await page.getByRole("button", { name: "删除当前工程" }).click();
  await page.getByRole("button", { name: "删除工程" }).click();
  await expect(page).toHaveURL(/\/projects$/, { timeout: 30_000 });

  // 3. 已删除工程不应出现在列表
  await expect(page.getByRole("heading", { name: "工程库" })).toBeVisible();
  await expect(page.locator(`[data-song-id="${songId}"]`)).toHaveCount(0, { timeout: 15_000 });
});

test("project A to B isolation: no stale data leak", async ({ page }) => {
  const songA = await createProjectViaApi("生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调");
  const songB = await createProjectViaApi("生成一首轻快的流行歌曲");

  // 打开工程 A
  await page.goto(`/projects/${songA}`);
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });
  const titleA = await page.locator(".workspace-header__title").first().textContent();

  // 返回工程库 → 打开工程 B
  await page.goto("/projects");
  await page.locator(`[data-song-id="${songB}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${songB}`));

  // B 不显示 A 的标题 / song_id
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });
  await expect(page).not.toHaveURL(new RegExp(`/projects/${songA}`));
  const titleB = await page.locator(".workspace-header__title").first().textContent();
  expect(titleB).not.toBe(titleA);
});

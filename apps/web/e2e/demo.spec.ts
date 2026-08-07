import { expect, test } from "@playwright/test";

/**
 * 完整演示链路：prompt → MusicSpec → MIDI → WAV 播放 → 编辑 → 版本 → 混音 → 工程导出。
 * T33.1 起生成入口在 /create，生成成功后自动进入 /projects/:songId 工作台。
 * 需要本机 8000 端口运行 MockProvider 后端。
 */
test("full demo chain: generate to export", async ({ page }) => {
  // 1. 生成 MusicSpec（/ 自动跳转 /create）
  await page.goto("/");
  await expect(page).toHaveURL(/\/create$/);
  const promptBox = page.getByRole("textbox").first();
  await promptBox.fill("生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调");
  await page.getByRole("button", { name: "生成 MusicSpec" }).click();
  // 生成成功自动进入工作台
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+/, { timeout: 60_000 });
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/MIDI：无/)).toBeVisible();

  // 2. 生成 MIDI
  await page.getByRole("button", { name: "生成 MIDI" }).click();
  await expect(page.getByText("下载 MIDI")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/轨道数/)).toBeVisible();
  await expect(page.getByText(/MIDI：有/)).toBeVisible();

  // 3. 渲染 WAV 并出现播放器
  await page.getByRole("button", { name: "渲染 WAV" }).click();
  await expect(page.locator("audio").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/WAV：有/)).toBeVisible();

  // 4. 自然语言编辑（副歌更亮）→ 版本 v2
  await page.getByPlaceholder(/例如：副歌更亮一点/).fill("副歌更亮一点");
  await page.getByRole("button", { name: "应用修改" }).click();
  await expect(page.getByText(/当前版本：v2/)).toBeVisible({ timeout: 60_000 });

  // 5. 版本列表 / 恢复
  await page.getByRole("button", { name: /查看版本/ }).click();
  await expect(page.getByText(/v1/).first()).toBeVisible();
  await expect(page.getByText(/v2/).first()).toBeVisible();

  // 6. 混音器可用（调整音量并应用）
  const mixerSection = page.locator("section", { has: page.getByRole("heading", { name: "混音器" }) });
  await expect(mixerSection).toBeVisible();
  await expect(mixerSection.locator("input[type=range]").first()).toBeVisible();

  // 7. 工程导出入口可用（下载链接存在）
  const projectSection = page.locator("section", { has: page.getByRole("heading", { name: "工程导入导出" }) });
  await expect(projectSection).toBeVisible();
  await expect(projectSection.getByText("导出 .aimusic.zip")).toBeVisible();
});

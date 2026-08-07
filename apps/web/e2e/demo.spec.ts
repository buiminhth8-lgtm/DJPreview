import { expect, test } from "@playwright/test";

/**
 * Flow A：/create → 生成 MusicSpec（MockProvider）→ 摘要 → 进入工作台 → MIDI → WAV。
 * T33.4 起生成成功后停留在 /create 摘要，需点击“进入工程工作台”。
 * 需要本机 8000 端口运行 MockProvider 后端。
 */
test("flow a: create to workspace midi wav", async ({ page }) => {
  // 1. / 自动跳转 /create
  await page.goto("/");
  await expect(page).toHaveURL(/\/create$/);

  // 2. 输入 prompt 并生成（包含 style_template_id / style_strength 的请求由后端校验）
  const promptBox = page.getByRole("textbox").first();
  await promptBox.fill("生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调");
  await page.getByRole("button", { name: "生成音乐" }).click();

  // 3. 生成成功 → 出现“进入工程工作台”（Link 元素）
  await expect(page.getByRole("link", { name: "进入工程工作台" })).toBeVisible({ timeout: 60_000 });

  // 4. 点击进入 → URL 变为 /projects/:songId
  await page.getByRole("link", { name: "进入工程工作台" }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+/, { timeout: 30_000 });

  // 5. 工作台加载（标题 + song_id）
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });

  // 6. 生成 MIDI（工作台可能有两个“生成 MIDI”按钮，取第一个可见的）
  const midiButton = page.getByRole("button", { name: "生成 MIDI" }).first();
  await midiButton.click();
  await expect(page.getByText("下载 MIDI").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/MIDI：有/).first()).toBeVisible({ timeout: 15_000 });

  // 7. 渲染 WAV 并出现播放器
  const renderButton = page.getByRole("button", { name: "渲染 WAV" }).first();
  await renderButton.click();
  await expect(page.locator("audio").first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/WAV：有/).first()).toBeVisible({ timeout: 15_000 });
});

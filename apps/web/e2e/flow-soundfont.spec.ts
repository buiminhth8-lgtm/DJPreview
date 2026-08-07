import { expect, test } from "@playwright/test";

/**
 * T33.7 语义浏览器验证：SoundFont 面板显示环境能力（FluidSynth 状态），
 * 不推断当前 WAV renderer；无 WAV 时不显示 fallback warning。
 * 需要本机 8000 端口运行 MockProvider + fallback 后端。
 */

async function createProjectViaApi(): Promise<string> {
  const response = await fetch("http://127.0.0.1:8000/api/v1/songs/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: "生成一段测试音乐" }),
  });
  const data = (await response.json()) as { song_id: string };
  return data.song_id;
}

test("soundfont panel shows environment diagnostics only", async ({ page }) => {
  const songId = await createProjectViaApi();
  await page.goto(`/projects/${songId}`);
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });

  // SoundFont 面板存在（环境能力：FluidSynth 可用/不可用 由 diagnostics 决定）
  await expect(page.getByRole("heading", { name: /SoundFont/ }).first()).toBeVisible({ timeout: 15_000 });

  // 无 WAV 时：不出现 fallback warning；显示 MIDI 尚未生成或暂无音频
  const fallbackNotice = page.getByText(/当前为预览级音色（fallback）/);
  await expect(fallbackNotice).toHaveCount(0);
});

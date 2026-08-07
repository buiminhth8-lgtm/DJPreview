import { expect, test } from "@playwright/test";

/**
 * T33-R4：真实 FluidSynth 渲染后的前端 Workspace 状态验证。
 * 需后端（AUDIO_RENDERER=auto + GeneralUser-GS.sf2 已放置 data/soundfonts/）在 8000 端口运行。
 * 测试内通过产品 API 创建工程 → 生成 MIDI → 选择 SoundFont → 渲染 WAV，
 * 然后验证 Workspace 显示 FluidSynth 且无 fallback warning。
 */

test("r4: workspace shows fluidsynth and no fallback warning", async ({ page }) => {
  // 1. 通过产品 API 创建工程并生成 MIDI
  const genResp = await fetch("http://127.0.0.1:8000/api/v1/songs/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: "生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调" }),
  });
  const { song_id } = (await genResp.json()) as { song_id: string };
  await fetch(`http://127.0.0.1:8000/api/v1/songs/${song_id}/midi/generate`, { method: "POST" });

  // 2. 选择 GeneralUser-GS（SoundFont 列表第一个；若环境无音源则跳过，不伪报）
  const sfListResp = await fetch("http://127.0.0.1:8000/api/v1/soundfonts");
  const sfList = (await sfListResp.json()) as { soundfonts: Array<{ id: string; name: string }> };
  const generalUser = sfList.soundfonts.find((s) => s.name.includes("GeneralUser-GS"));
  if (!generalUser) {
    test.skip(true, "GeneralUser-GS 未发现，真实渲染链路未验证（NOT_VERIFIED）");
    return;
  }
  await fetch(`http://127.0.0.1:8000/api/v1/songs/${song_id}/soundfont`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ soundfont_id: generalUser.id }),
  });

  // 3. 真实渲染 WAV（AUDIO_RENDERER=auto → FluidSynth）
  const renderResp = await fetch(`http://127.0.0.1:8000/api/v1/songs/${song_id}/audio/render`, {
    method: "POST",
  });
  expect(renderResp.ok).toBeTruthy();

  // 4. 打开 Workspace 验证 UI 状态
  await page.goto(`/projects/${song_id}`);
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });

  // 渲染器状态：显示 FluidSynth 与 GeneralUser-GS
  await expect(page.getByText("FluidSynth").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("GeneralUser-GS").first()).toBeVisible({ timeout: 15_000 });

  // 不显示 fallback warning
  await expect(page.getByText("当前为预览级音色（fallback）")).toHaveCount(0);

  // 刷新后状态保持
  await page.reload();
  await expect(page.getByText(/song_id：/).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("GeneralUser-GS").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("当前为预览级音色（fallback）")).toHaveCount(0);
});

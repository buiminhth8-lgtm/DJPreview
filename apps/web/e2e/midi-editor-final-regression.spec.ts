import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type EditorNote = {
  id: string;
  pitch: number;
  start_tick: number;
  duration_tick: number;
  velocity: number;
  channel: number;
};

type EditorDocument = {
  version_id: string;
  tracks: Array<{ id: string; role: string | null; channel: number; notes: EditorNote[] }>;
};

type VersionState = {
  current_version_id: string;
  versions: Array<{ version_id: string; version_number: number }>;
};

async function createProjectFromUi(page: Page): Promise<string> {
  await page.goto("/create");
  await page.getByLabel("一句话描述你想要的音乐").fill("欢快电子配乐，包含 Melody、Bass、Drums 和 Pad，96 BPM");
  await page.getByRole("button", { name: "生成音乐" }).click();
  const enter = page.getByRole("link", { name: "进入工程工作台" });
  await expect(enter).toBeVisible({ timeout: 60_000 });
  const href = await enter.getAttribute("href");
  expect(href).toMatch(/^\/projects\/[0-9a-f-]+$/);
  const songId = decodeURIComponent(href!.split("/").at(-1)!);
  await enter.click();
  return songId;
}

async function ensureMidi(page: Page, request: APIRequestContext, songId: string) {
  const generate = page.getByRole("button", { name: "生成 MIDI", exact: true }).first();
  await expect(generate).toBeEnabled({ timeout: 30_000 });
  const response = page.waitForResponse(
    (candidate) => candidate.request().method() === "POST" && candidate.url().endsWith(`/songs/${songId}/midi/generate`),
  );
  await generate.click();
  expect((await response).ok()).toBeTruthy();
  await expect.poll(async () => {
    const assets = await request.get(`${API}/songs/${songId}/assets`);
    return assets.ok() && Boolean((await assets.json()).has_midi);
  }, { timeout: 30_000 }).toBe(true);
}

async function visibleEditor(page: Page) {
  const editor = page.locator(".midi-editor:visible").first();
  await expect(editor).toBeVisible({ timeout: 30_000 });
  return editor;
}

async function makeBassDirty(editor: Awaited<ReturnType<typeof visibleEditor>>) {
  await editor.getByRole("option", { name: /bass/i }).first().click();
  await editor.locator("[data-note-id]").first().click();
  const velocity = editor.getByLabel("Velocity 力度");
  const currentVelocity = Number(await velocity.inputValue());
  await velocity.fill(currentVelocity === 77 ? "78" : "77");
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();
}

async function versions(request: APIRequestContext, songId: string): Promise<VersionState> {
  return await (await request.get(`${API}/songs/${songId}/versions`)).json() as VersionState;
}

test("T34.10 Generate, dirty guards, conflict, save, render, restore and project isolation", async ({ page, request }) => {
  const songId = await createProjectFromUi(page);
  await ensureMidi(page, request, songId);
  let editor = await visibleEditor(page);
  await makeBassDirty(editor);

  const baseDocument = await (await request.get(`${API}/songs/${songId}/midi/editor`)).json() as EditorDocument;
  const baseSpec = (await (await request.get(`${API}/songs/${songId}`)).json()).music_spec;
  const initialVersionCount = (await versions(request, songId)).versions.length;

  // SPA navigation: Continue Editing must retain the Draft; Discard must leave cleanly.
  await page.locator(".workspace-header__back").filter({ hasText: "工程库" }).first().click();
  const navigationGuard = page.getByRole("dialog", { name: "保留 MIDI 草稿？" });
  await expect(navigationGuard).toBeVisible();
  await navigationGuard.getByRole("button", { name: "继续编辑" }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${songId}$`));
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();

  // Regenerate guard must not issue a mutation until Discard is chosen.
  let regenerateRequests = 0;
  page.on("request", (outgoing) => {
    if (outgoing.method() === "POST" && outgoing.url().endsWith(`/songs/${songId}/midi/generate`)) {
      regenerateRequests += 1;
    }
  });
  await page.getByRole("button", { name: "生成 MIDI", exact: true }).first().click();
  const regenerateGuard = page.getByRole("dialog", { name: "放弃 MIDI 草稿？" });
  await expect(regenerateGuard).toBeVisible();
  expect(regenerateRequests).toBe(0);
  await regenerateGuard.getByRole("button", { name: "继续编辑" }).click();
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();
  expect(regenerateRequests).toBe(0);

  // Existing optimize/mix actions also regenerate canonical MIDI and must share the same guard.
  let optimizeRequests = 0;
  let mixApplyRequests = 0;
  page.on("request", (outgoing) => {
    if (outgoing.method() === "POST" && outgoing.url().endsWith(`/songs/${songId}/quality/optimize`)) optimizeRequests += 1;
    if (outgoing.method() === "POST" && outgoing.url().endsWith(`/songs/${songId}/mix/apply`)) mixApplyRequests += 1;
  });
  await page.getByRole("button", { name: "自动优化", exact: true }).click();
  await expect(regenerateGuard).toBeVisible();
  expect(optimizeRequests).toBe(0);
  await regenerateGuard.getByRole("button", { name: "继续编辑" }).click();
  const mixApply = page.getByRole("button", { name: "应用混音并重新渲染", exact: true });
  await expect(mixApply).toBeEnabled({ timeout: 30_000 });
  await mixApply.click();
  await expect(regenerateGuard).toBeVisible();
  expect(mixApplyRequests).toBe(0);
  await regenerateGuard.getByRole("button", { name: "继续编辑" }).click();
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();

  await page.locator(".workspace-header__back").filter({ hasText: "工程库" }).first().click();
  await navigationGuard.getByRole("button", { name: "放弃草稿并离开" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await page.locator(`[data-song-id="${songId}"]`).getByRole("button", { name: "打开工程", exact: true }).click();
  editor = await visibleEditor(page);
  await expect(editor.getByText(/未保存修改/)).toHaveCount(0);
  await expect(editor.getByTestId("selected-note-count")).toHaveText("Selected: 0");
  await expect(editor.getByRole("button", { name: /编辑/ })).toHaveAttribute("aria-pressed", "false");

  // Browser refresh/close: dirty drafts must register the native beforeunload guard.
  await makeBassDirty(editor);
  const refreshGuarded = await page.evaluate(() => {
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  });
  expect(refreshGuarded).toBe(true);
  await editor.getByRole("button", { name: "放弃修改" }).click();
  await editor.locator(".ui-dialog").filter({ hasText: "放弃修改？" }).getByRole("button", { name: "放弃修改" }).click();

  // Version conflict: retain the old Draft and never overwrite the concurrent version.
  await makeBassDirty(editor);
  const bass = baseDocument.tracks.find((track) => track.role === "bass")!;
  const concurrent = await request.post(`${API}/songs/${songId}/midi/edit`, {
    data: {
      track_id: bass.id,
      base_version_id: baseDocument.version_id,
      notes: bass.notes.map((note, index) => index === 0 ? { ...note, velocity: 66 } : note),
    },
  });
  expect(concurrent.ok()).toBeTruthy();
  const concurrentVersion = (await concurrent.json()).version_id as string;
  await editor.getByRole("button", { name: "保存 MIDI 修改" }).click();
  const conflict = page.locator(".ui-dialog").filter({ hasText: "版本冲突" });
  await expect(conflict).toBeVisible();
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();
  expect((await versions(request, songId)).current_version_id).toBe(concurrentVersion);
  await conflict.getByRole("button", { name: "重新加载最新版本" }).click();
  await expect(editor.getByText(/未保存修改/)).toHaveCount(0);
  await expect(editor.getByText(`Version: ${concurrentVersion}`)).toBeVisible();

  // Render an authoritative old WAV, then save one manual edit: exactly one new version and stale UI.
  const firstRender = await request.post(`${API}/songs/${songId}/audio/render`);
  expect(firstRender.ok()).toBeTruthy();
  const oldRenderMeta = (await firstRender.json()).metadata;
  await page.reload();
  editor = await visibleEditor(page);
  await makeBassDirty(editor);
  let saveRequests = 0;
  page.on("request", (outgoing) => {
    if (outgoing.method() === "POST" && outgoing.url().endsWith(`/songs/${songId}/midi/edit`)) saveRequests += 1;
  });
  const beforeSave = await versions(request, songId);
  await editor.getByRole("button", { name: "保存 MIDI 修改" }).click();
  await expect(editor.getByText(`Version: v${beforeSave.versions.length + 1}`)).toBeVisible({ timeout: 60_000 });
  expect(saveRequests).toBe(1);
  const manualVersion = (await versions(request, songId)).current_version_id;
  expect((await versions(request, songId)).versions.length).toBe(beforeSave.versions.length + 1);
  expect((await (await request.get(`${API}/songs/${songId}`)).json()).music_spec).toEqual(baseSpec);
  await expect(page.getByRole("list", { name: "工作台状态" }).first()).toContainText("WAV：需重新渲染");
  const staleAssets = await (await request.get(`${API}/songs/${songId}/assets`)).json();
  expect(staleAssets.audio_needs_render).toBe(true);
  expect(staleAssets.audio.metadata.renderer).toBe(oldRenderMeta.renderer);
  expect(staleAssets.audio.metadata.is_fallback).toBe(oldRenderMeta.is_fallback);
  expect(staleAssets.audio.metadata.fallback_reason).toBe(oldRenderMeta.fallback_reason);

  // A direct refresh must not relabel the old WAV as current.
  await page.reload();
  editor = await visibleEditor(page);
  await expect(page.getByRole("list", { name: "工作台状态" }).first()).toContainText("WAV：需重新渲染");

  const rerenderResponse = page.waitForResponse(
    (candidate) => candidate.request().method() === "POST" && candidate.url().endsWith(`/songs/${songId}/audio/render`),
  );
  await page.getByRole("button", { name: "渲染 WAV", exact: true }).first().click();
  const rerender = await rerenderResponse;
  expect(rerender.ok()).toBeTruthy();
  const rerenderMeta = (await rerender.json()).metadata;
  await expect(page.getByRole("list", { name: "工作台状态" }).first()).toContainText("WAV：有");
  expect((await (await request.get(`${API}/songs/${songId}/assets`)).json()).audio_needs_render).toBe(false);
  expect(rerenderMeta.renderer).toBe("fallback");
  expect(rerenderMeta.is_fallback).toBe(true);
  expect(rerenderMeta.fallback_reason).toBeTruthy();

  // Restore generated/concurrent version, then return to the manual edit version.
  await page.getByRole("button", { name: "刷新版本" }).click();
  const concurrentItem = page.locator(".workspace-version-item").filter({ hasText: concurrentVersion }).first();
  await makeBassDirty(editor);
  await concurrentItem.getByRole("button", { name: "恢复此版本" }).click();
  const restoreGuard = page.getByRole("dialog", { name: "放弃 MIDI 草稿？" });
  await expect(restoreGuard).toBeVisible();
  await restoreGuard.getByRole("button", { name: "继续编辑" }).click();
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();
  expect((await versions(request, songId)).current_version_id).toBe(manualVersion);

  await concurrentItem.getByRole("button", { name: "恢复此版本" }).click();
  await restoreGuard.getByRole("button", { name: "放弃草稿并继续" }).click();
  await expect(editor.getByText(`Version: ${concurrentVersion}`)).toBeVisible({ timeout: 60_000 });
  await expect(editor.getByTestId("selected-note-count")).toHaveText("Selected: 0");
  await expect(editor.getByText(/未保存修改/)).toHaveCount(0);

  await page.getByRole("button", { name: "刷新版本" }).click();
  const manualItem = page.locator(".workspace-version-item").filter({ hasText: manualVersion }).first();
  page.once("dialog", (dialog) => dialog.accept());
  await manualItem.getByRole("button", { name: "恢复此版本" }).click();
  await expect(editor.getByText(`Version: ${manualVersion}`)).toBeVisible({ timeout: 60_000 });

  // Project A -> B drops all Editor transient state; returning A follows the saved policy.
  const projectB = await request.post(`${API}/songs/generate`, { data: { prompt: "忧郁雨夜 D minor 配乐，包含 Bass 和 Drums" } });
  expect(projectB.ok()).toBeTruthy();
  const songB = (await projectB.json()).song_id as string;
  expect((await request.post(`${API}/songs/${songB}/midi/generate`)).ok()).toBeTruthy();
  await page.goto(`/projects/${songB}`);
  const editorB = await visibleEditor(page);
  await expect(editorB.getByText(`Version: v1`)).toBeVisible();
  await expect(editorB.getByText(/未保存修改/)).toHaveCount(0);
  await expect(editorB.getByTestId("selected-note-count")).toHaveText("Selected: 0");
  await page.goto(`/projects/${songId}`);
  editor = await visibleEditor(page);
  await expect(editor.getByText(`Version: ${manualVersion}`)).toBeVisible();
  await expect(editor.getByText(/未保存修改/)).toHaveCount(0);
  expect((await versions(request, songId)).versions.length).toBe(initialVersionCount + 2);
});

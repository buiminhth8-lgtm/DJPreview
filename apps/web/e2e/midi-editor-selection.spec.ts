import { expect, test } from "@playwright/test";

const API = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type NoteTitle = { name: string; start: number; duration: number };

function parseTitle(value: string): NoteTitle {
  const match = value.match(/^(\S+) start=(\d+) dur=(\d+)$/);
  if (!match) throw new Error(`Unexpected note title: ${value}`);
  return { name: match[1], start: Number(match[2]), duration: Number(match[3]) };
}

test("T34.8 real Bass selection, clipboard, lock, preview and one-save boundary", async ({ page, request }) => {
  const generated = await request.post(`${API}/songs/generate`, {
    data: { prompt: "生成一段带 Bass、Melody 和 Drums 的电子配乐，96 BPM" },
  });
  expect(generated.ok()).toBeTruthy();
  const songId = (await generated.json()).song_id as string;
  expect((await request.post(`${API}/songs/${songId}/midi/generate`)).ok()).toBeTruthy();
  expect((await request.post(`${API}/songs/${songId}/audio/render`)).ok()).toBeTruthy();

  const initialAssets = await (await request.get(`${API}/songs/${songId}/assets`)).json() as {
    has_audio: boolean;
    current_version: { version_id: string; version_number: number };
  };
  expect(initialAssets.has_audio).toBe(true);

  let saveRequestCount = 0;
  let lastPreviewPayload: { tracks: Array<{ track_id: string; notes: Array<{ id: string; velocity: number }> }> } | null = null;
  page.on("request", (outgoing) => {
    if (outgoing.method() === "POST" && /\/midi\/edit$/.test(outgoing.url())) saveRequestCount += 1;
    if (outgoing.method() === "POST" && /\/midi\/preview$/.test(outgoing.url())) {
      lastPreviewPayload = outgoing.postDataJSON();
    }
  });

  await page.goto(`/projects/${songId}`);
  const editor = page.locator(".midi-editor:visible").first();
  // The API setup already generated canonical MIDI. A slow page load must not
  // regenerate it and silently alter the version chain under test.
  await expect(editor).toBeVisible({ timeout: 30_000 });
  await editor.getByRole("option", { name: /bass/i }).first().click();
  const roll = editor.locator("[data-note-count]");
  const initialNoteCount = Number(await roll.getAttribute("data-note-count"));
  expect(initialNoteCount).toBeGreaterThan(10);

  const grid = editor.locator(".midi-editor__grid");
  await grid.scrollIntoViewIfNeeded();
  await grid.evaluate((element) => {
    const targets = Array.from(element.querySelectorAll<SVGGElement>("[data-note-id]")).slice(3, 6);
    const boxes = targets.map((target) => target.getBBox());
    element.scrollLeft = Math.max(0, Math.min(...boxes.map((box) => box.x)) - 24);
    element.scrollTop = Math.max(0, Math.min(...boxes.map((box) => box.y)) - 24);
  });
  await grid.scrollIntoViewIfNeeded();
  const firstThree = editor.locator("[data-note-id]");
  const boxes = await Promise.all([3, 4, 5].map((index) => firstThree.nth(index).boundingBox()));
  const visibleBoxes = boxes.filter((box): box is NonNullable<typeof box> => box != null);
  expect(visibleBoxes).toHaveLength(3);
  const gridBox = await grid.boundingBox();
  expect(gridBox).not.toBeNull();
  const startX = Math.max(gridBox!.x + 2, Math.min(...visibleBoxes.map((box) => box.x)) - 8);
  const startY = Math.max(gridBox!.y + 2, Math.min(...visibleBoxes.map((box) => box.y)) - 8);
  const endX = Math.min(gridBox!.x + gridBox!.width - 2, Math.max(...visibleBoxes.map((box) => box.x + box.width)) + 8);
  const endY = Math.min(gridBox!.y + gridBox!.height - 2, Math.max(...visibleBoxes.map((box) => box.y + box.height)) + 8);
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(endX, endY, { steps: 8 });
  await page.mouse.up();

  const selected = editor.locator(".midi-editor__note-group.is-selected");
  const groupSize = await selected.count();
  expect(groupSize).toBeGreaterThanOrEqual(3);
  await expect(editor.getByTestId("selected-note-count")).toHaveText(`Selected: ${groupSize}`);

  const titlesBefore = (await selected.locator("title").allTextContents()).map(parseTitle);
  const visibleGridBox = await grid.boundingBox();
  let anchorBox = null as Awaited<ReturnType<typeof selected.boundingBox>>;
  let anchorIndex = -1;
  for (let index = 0; index < groupSize; index += 1) {
    const candidate = await selected.nth(index).boundingBox();
    if (
      candidate && visibleGridBox &&
      candidate.x + 8 >= visibleGridBox.x &&
      candidate.x + 8 <= visibleGridBox.x + visibleGridBox.width &&
      candidate.y + candidate.height / 2 >= visibleGridBox.y &&
      candidate.y + candidate.height / 2 <= visibleGridBox.y + visibleGridBox.height
    ) {
      anchorBox = candidate;
      anchorIndex = index;
      break;
    }
  }
  expect(anchorBox).not.toBeNull();
  await page.mouse.move(anchorBox!.x + 8, anchorBox!.y + anchorBox!.height / 2);
  await page.mouse.down();
  await page.mouse.move(anchorBox!.x + 68, anchorBox!.y - 12 + anchorBox!.height / 2, { steps: 6 });
  await page.mouse.up();
  const titlesMoved = (await selected.locator("title").allTextContents()).map(parseTitle);
  const tickDelta = titlesMoved[0].start - titlesBefore[0].start;
  expect(tickDelta).not.toBe(0);
  expect(anchorIndex).toBeGreaterThanOrEqual(0);
  expect(titlesMoved[anchorIndex].start % 120).toBe(0);
  expect(titlesMoved.map((note, index) => note.start - titlesBefore[index].start)).toEqual(
    Array(groupSize).fill(tickDelta),
  );
  expect(titlesMoved.map((note) => note.duration)).toEqual(titlesBefore.map((note) => note.duration));

  await editor.press("Control+z");
  expect((await selected.locator("title").allTextContents()).map(parseTitle)).toEqual(titlesBefore);
  await editor.press("Control+y");
  expect((await selected.locator("title").allTextContents()).map(parseTitle)).toEqual(titlesMoved);

  await editor.press("Control+c");
  await expect(editor.getByText(`已复制 ${groupSize} 个音符`)).toBeVisible();
  const timeline = editor.getByRole("slider", { name: /MIDI 时间轴/ });
  const timelineScroll = editor.locator(".midi-editor__timeline-scroll");
  const timelineBox = await timelineScroll.boundingBox();
  expect(timelineBox).not.toBeNull();
  await page.mouse.click(timelineBox!.x + timelineBox!.width * 0.65, timelineBox!.y + timelineBox!.height / 2);
  const playheadTick = Number(await timeline.getAttribute("aria-valuenow"));
  expect(playheadTick).toBeGreaterThan(0);

  await editor.press("Control+v");
  await expect(roll).toHaveAttribute("data-note-count", String(initialNoteCount + groupSize));
  const pastedIds = await selected.evaluateAll((elements) => elements.map((element) => element.getAttribute("data-note-id")));
  expect(pastedIds).toHaveLength(groupSize);
  expect(pastedIds.every((id) => id?.startsWith("draft:"))).toBe(true);
  const pastedTitles = (await selected.locator("title").allTextContents()).map(parseTitle);
  expect(Math.min(...pastedTitles.map((note) => note.start))).toBe(Math.round(playheadTick / 120) * 120);

  const pastedSpanStart = Math.min(...pastedTitles.map((note) => note.start));
  const pastedSpanEnd = Math.max(...pastedTitles.map((note) => note.start + note.duration));
  await editor.press("Control+d");
  await expect(roll).toHaveAttribute("data-note-count", String(initialNoteCount + groupSize * 2));
  const duplicateIds = await selected.evaluateAll((elements) => elements.map((element) => element.getAttribute("data-note-id")));
  expect(new Set([...pastedIds, ...duplicateIds]).size).toBe(groupSize * 2);
  const duplicateTitles = (await selected.locator("title").allTextContents()).map(parseTitle);
  expect(duplicateTitles.map((note) => note.start)).toEqual(
    pastedTitles.map((note) => note.start + pastedSpanEnd - pastedSpanStart),
  );

  await editor.getByLabel("Batch velocity 力度").fill("55");
  await expect(editor.locator(".midi-editor__selection-summary")).toContainText("avg velocity 55");
  await editor.press("Delete");
  await expect(roll).toHaveAttribute("data-note-count", String(initialNoteCount + groupSize));
  await editor.press("Control+z");
  await expect(roll).toHaveAttribute("data-note-count", String(initialNoteCount + groupSize * 2));

  await editor.locator("[data-note-id]").first().click();
  await editor.getByRole("button", { name: /编辑/ }).click();
  await editor.press("Control+c");
  await expect(editor.getByText("已复制 1 个音符")).toBeVisible();
  const lockedCount = await roll.getAttribute("data-note-count");
  await editor.press("Delete");
  await editor.press("Control+v");
  await editor.press("Control+d");
  await expect(roll).toHaveAttribute("data-note-count", lockedCount!);

  const previewResponse = page.waitForResponse(
    (response) => response.request().method() === "POST" && /\/midi\/preview$/.test(response.url()),
  );
  await editor.getByRole("button", { name: /Play/ }).click();
  expect((await previewResponse).ok()).toBeTruthy();
  await expect(editor.getByRole("button", { name: /Stop/ })).toBeEnabled({ timeout: 30_000 });
  expect(lastPreviewPayload).not.toBeNull();
  const previewPayload = lastPreviewPayload as NonNullable<typeof lastPreviewPayload>;
  const bassPreview = previewPayload.tracks.find((track) => /bass/i.test(track.track_id));
  expect(bassPreview?.notes.some((note) => note.id.startsWith("draft:") && note.velocity === 55)).toBe(true);
  await editor.getByRole("button", { name: /Stop/ }).click();

  await editor.getByRole("button", { name: "保存 MIDI 修改" }).click();
  await expect(editor.getByText(`Version: v${initialAssets.current_version.version_number + 1}`)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("list", { name: "工作台状态" }).first()).toContainText("WAV：需重新渲染");
  expect(saveRequestCount).toBe(1);
  const finalAssets = await (await request.get(`${API}/songs/${songId}/assets`)).json() as {
    has_audio: boolean;
    current_version: { version_number: number };
  };
  expect(finalAssets.current_version.version_number).toBe(initialAssets.current_version.version_number + 1);
  // Save does not render or delete the formal WAV; Workspace marks the existing audio as stale.
  expect(finalAssets.has_audio).toBe(true);
});

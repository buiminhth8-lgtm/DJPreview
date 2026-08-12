import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8000/api/v1";

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

type PerformanceResult = {
  count: number;
  initialMs: number;
  zoomMs: number;
  panMs: number;
  singleEditMs: number;
  selectAllMs: number;
  batchVelocityMs: number;
  batchMoveMs: number;
  undoMs: number;
  previewMs?: number;
};

async function createSizedProject(request: APIRequestContext, count: number): Promise<string> {
  const created = await request.post(`${API}/songs/generate`, {
    data: { prompt: `T34-R performance ${count} notes C major bass drums` },
  });
  expect(created.ok()).toBeTruthy();
  const songId = (await created.json()).song_id as string;
  expect((await request.post(`${API}/songs/${songId}/midi/generate`)).ok()).toBeTruthy();
  const document = await (await request.get(`${API}/songs/${songId}/midi/editor`)).json() as EditorDocument;
  const bass = document.tracks.find((track) => track.role === "bass")!;
  const notes: EditorNote[] = Array.from({ length: count }, (_, index) => ({
    id: `perf-${count}-${index}`,
    pitch: 36 + (index % 12),
    start_tick: index * 20,
    duration_tick: 18,
    velocity: 70 + (index % 30),
    channel: bass.channel,
  }));
  const saved = await request.post(`${API}/songs/${songId}/midi/edit`, {
    data: {
      track_id: bass.id,
      base_version_id: document.version_id,
      notes,
    },
  });
  expect(saved.ok()).toBeTruthy();
  return songId;
}

async function measureEditor(page: Page, songId: string, count: number): Promise<PerformanceResult> {
  const initialStarted = performance.now();
  await page.goto(`/projects/${songId}`);
  const editor = page.locator(".midi-editor");
  await expect(editor).toBeVisible({ timeout: 30_000 });
  await editor.getByRole("option", { name: /bass/i }).first().click();
  const notes = editor.locator("[data-note-id]");
  await expect(notes).toHaveCount(count, { timeout: 30_000 });
  const initialMs = performance.now() - initialStarted;

  const zoomStarted = performance.now();
  await editor.getByRole("button", { name: "横向放大" }).click();
  await editor.getByRole("button", { name: "横向缩小" }).click();
  await editor.getByRole("button", { name: "纵向放大" }).click();
  const zoomMs = performance.now() - zoomStarted;

  const panStarted = performance.now();
  const pan = await editor.locator(".midi-editor__timeline-scroll").evaluate((element) => {
    (element as HTMLElement).scrollLeft = 800;
    element.dispatchEvent(new Event("scroll", { bubbles: true }));
    return (element as HTMLElement).scrollLeft;
  });
  const panMs = performance.now() - panStarted;
  expect(pan).toBeGreaterThan(0);

  const editStarted = performance.now();
  await notes.first().click();
  const velocity = editor.getByRole("spinbutton", { name: "Velocity 力度" });
  const originalVelocity = Number(await velocity.inputValue());
  await velocity.fill(originalVelocity === 77 ? "78" : "77");
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();
  const singleEditMs = performance.now() - editStarted;

  const selectStarted = performance.now();
  await editor.press("Control+a");
  await expect(editor.getByTestId("selected-note-count")).toHaveText(`Selected: ${count}`);
  const selectAllMs = performance.now() - selectStarted;

  const batchStarted = performance.now();
  await editor.getByRole("spinbutton", { name: "Batch Velocity" }).fill("88");
  const batchVelocityMs = performance.now() - batchStarted;
  await editor.getByRole("button", { name: "Undo" }).click();

  const anchor = notes.nth(Math.min(100, count - 1));
  await anchor.scrollIntoViewIfNeeded();
  const anchorBox = await anchor.boundingBox();
  expect(anchorBox).not.toBeNull();
  const title = anchor.locator("title");
  const titleBefore = await title.textContent();
  const batchMoveStarted = performance.now();
  await page.mouse.move(anchorBox!.x + Math.min(8, anchorBox!.width / 2), anchorBox!.y + anchorBox!.height / 2);
  await page.mouse.down();
  await page.mouse.move(anchorBox!.x + Math.min(8, anchorBox!.width / 2) + 60, anchorBox!.y + anchorBox!.height / 2, { steps: 6 });
  await page.mouse.up();
  await expect(title).not.toHaveText(titleBefore!);
  const batchMoveMs = performance.now() - batchMoveStarted;

  const undoStarted = performance.now();
  await editor.getByRole("button", { name: "Undo" }).click();
  await expect(title).toHaveText(titleBefore!);
  const undoMs = performance.now() - undoStarted;

  return { count, initialMs, zoomMs, panMs, singleEditMs, selectAllMs, batchVelocityMs, batchMoveMs, undoMs };
}

test("T34-R 500/1000/3000-note editor remains usable", async ({ page, request }) => {
  const results: PerformanceResult[] = [];
  for (const count of [500, 1000, 3000]) {
    const songId = await createSizedProject(request, count);
    const result = await measureEditor(page, songId, count);
    results.push(result);

    expect(result.initialMs).toBeLessThan(15_000);
    expect(Math.max(
      result.zoomMs,
      result.panMs,
      result.singleEditMs,
      result.selectAllMs,
      result.batchVelocityMs,
      result.batchMoveMs,
      result.undoMs,
    ))
      .toBeLessThan(10_000);

    if (count === 3000) {
      const editor = page.locator(".midi-editor");
      const previewStarted = performance.now();
      await editor.getByRole("button", { name: "▶ Play" }).click();
      await expect(editor.getByRole("button", { name: "■ Stop" })).toBeEnabled({ timeout: 30_000 });
      result.previewMs = performance.now() - previewStarted;
      await editor.getByRole("button", { name: "■ Stop" }).click();
      expect(result.previewMs).toBeLessThan(30_000);
    }
  }

  console.log(`T34-R PERFORMANCE ${JSON.stringify(results)}`);
});

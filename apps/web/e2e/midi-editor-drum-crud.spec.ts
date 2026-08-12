import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type EditorNote = {
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

function parseNoteTitle(value: string) {
  const match = value.match(/^\S+ start=(\d+) dur=(\d+)$/);
  if (!match) throw new Error(`Unexpected note title: ${value}`);
  return { startTick: Number(match[1]), durationTick: Number(match[2]) };
}

async function createMidiProject(request: APIRequestContext): Promise<string> {
  const created = await request.post(`${API}/songs/generate`, {
    data: { prompt: "T34-R 鼓轨 CRUD 验收，包含 Melody、Bass、Drums 和 Pad，96 BPM" },
  });
  expect(created.ok()).toBeTruthy();
  const songId = (await created.json()).song_id as string;
  expect((await request.post(`${API}/songs/${songId}/midi/generate`)).ok()).toBeTruthy();
  return songId;
}

async function editorFor(page: Page, songId: string) {
  await page.goto(`/projects/${songId}`);
  const editor = page.locator(".midi-editor:visible").first();
  await expect(editor).toBeVisible({ timeout: 30_000 });
  await editor.getByRole("option", { name: /drums/i }).first().click();
  return editor;
}

test("T34-R drum CRUD keeps GM pitch/channel through zoom, preview, save and reload", async ({ page, request }) => {
  const songId = await createMidiProject(request);
  const before = await (await request.get(`${API}/songs/${songId}/midi/editor`)).json() as EditorDocument;
  const drumBefore = before.tracks.find((track) => track.role === "drums")!;
  const initialCount = drumBefore.notes.length;
  expect(drumBefore.channel).toBe(9);
  expect(initialCount).toBeGreaterThan(0);

  let previewPayload: { tracks: Array<{ track_id: string; notes: Array<EditorNote & { id: string }> }> } | null = null;
  let saveRequests = 0;
  page.on("request", (outgoing) => {
    if (outgoing.method() === "POST" && outgoing.url().endsWith(`/songs/${songId}/midi/preview`)) {
      previewPayload = outgoing.postDataJSON();
    }
    if (outgoing.method() === "POST" && outgoing.url().endsWith(`/songs/${songId}/midi/edit`)) saveRequests += 1;
  });

  let editor = await editorFor(page, songId);
  await expect(editor.getByText("Kick").first()).toBeVisible();
  await expect(editor.getByText("Snare").first()).toBeVisible();

  // Exercise geometry with ~200% horizontal zoom, vertical zoom and non-zero scroll.
  for (let index = 0; index < 3; index += 1) await editor.getByRole("button", { name: "横向放大" }).click();
  for (let index = 0; index < 8; index += 1) await editor.getByRole("button", { name: "纵向放大" }).click();
  const grid = editor.locator(".midi-editor__grid");
  const scrolled = await grid.evaluate((element) => {
    element.scrollLeft = 600;
    element.scrollTop = 80;
    element.dispatchEvent(new Event("scroll", { bubbles: true }));
    return { left: element.scrollLeft, top: element.scrollTop };
  });
  expect(scrolled.left).toBeGreaterThan(0);
  expect(scrolled.top).toBeGreaterThan(0);

  // Dispatch on the canonical GM Snare row so another note cannot steal the hit target.
  const snareRow = grid.locator('[data-midi-pitch="38"]').first();
  const point = await snareRow.evaluate((element) => {
    const row = element.getBoundingClientRect();
    const gridElement = element.closest(".midi-editor__grid")!;
    const viewport = gridElement.getBoundingClientRect();
    return {
      x: viewport.left + viewport.width * 0.75,
      y: row.top + row.height / 2,
    };
  });
  await snareRow.dispatchEvent("dblclick", { clientX: point.x, clientY: point.y, button: 0 });

  const roll = editor.locator("[data-note-count]");
  await expect(roll).toHaveAttribute("data-note-count", String(initialCount + 1));
  let selected = editor.locator("[data-note-id].is-selected").first();
  expect(await selected.getAttribute("data-note-id")).toMatch(/^draft:/);

  // Move time + pitch, then resize, all while zoomed and scrolled.
  let box = await selected.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.move(box!.x + Math.min(10, box!.width / 2), box!.y + box!.height / 2);
  await page.mouse.down();
  await page.mouse.move(box!.x + Math.min(10, box!.width / 2) + 95, box!.y - 18 + box!.height / 2, { steps: 8 });
  await page.mouse.up();

  selected = editor.locator("[data-note-id].is-selected").first();
  const moved = parseNoteTitle(await selected.locator("title").textContent() ?? "");
  const resize = selected.locator(".midi-editor__resize");
  box = await resize.boundingBox();
  expect(box).not.toBeNull();
  const resizeStart = { x: box!.x + box!.width / 2, y: box!.y + box!.height / 2 };
  await resize.dispatchEvent("pointerdown", { pointerId: 41, button: 0, clientX: resizeStart.x, clientY: resizeStart.y });
  await resize.dispatchEvent("pointermove", { pointerId: 41, button: 0, clientX: resizeStart.x + 95, clientY: resizeStart.y });
  await resize.dispatchEvent("pointerup", { pointerId: 41, button: 0, clientX: resizeStart.x + 95, clientY: resizeStart.y });
  const resized = parseNoteTitle(await selected.locator("title").textContent() ?? "");
  expect(resized.durationTick).toBeGreaterThan(moved.durationTick);

  await editor.getByLabel("Velocity 力度").fill("93");
  await editor.press("Control+c");
  await editor.press("Control+v");
  await expect(roll).toHaveAttribute("data-note-count", String(initialCount + 2));
  await editor.press("Delete");
  await expect(roll).toHaveAttribute("data-note-count", String(initialCount + 1));
  await editor.press("Control+z");
  await expect(roll).toHaveAttribute("data-note-count", String(initialCount + 2));
  await editor.press("Control+y");
  await expect(roll).toHaveAttribute("data-note-count", String(initialCount + 1));

  const previewResponse = page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().endsWith(`/songs/${songId}/midi/preview`),
  );
  await editor.getByRole("button", { name: "▶ Play" }).click();
  expect((await previewResponse).ok()).toBeTruthy();
  await expect(editor.getByRole("button", { name: "■ Stop" })).toBeEnabled({ timeout: 30_000 });
  const payload = previewPayload as NonNullable<typeof previewPayload>;
  const previewDrums = payload.tracks.find((track) => track.track_id === drumBefore.id)!;
  expect(previewDrums.notes.some((note) => note.id.startsWith("draft:") && note.velocity === 93 && note.channel === 9)).toBe(true);
  await editor.getByRole("button", { name: "■ Stop" }).click();

  await editor.getByRole("button", { name: "保存 MIDI 修改" }).click();
  await expect(editor.getByText("Version: v2")).toBeVisible({ timeout: 60_000 });
  expect(saveRequests).toBe(1);

  await page.reload();
  editor = await editorFor(page, songId);
  await expect(editor.locator("[data-note-count]")).toHaveAttribute("data-note-count", String(initialCount + 1));
  const after = await (await request.get(`${API}/songs/${songId}/midi/editor`)).json() as EditorDocument;
  const drumAfter = after.tracks.find((track) => track.id === drumBefore.id)!;
  expect(drumAfter.channel).toBe(9);
  expect(drumAfter.notes).toHaveLength(initialCount + 1);
  expect(drumAfter.notes.every((note) => note.channel === 9)).toBe(true);
  expect(drumAfter.notes.some((note) => note.velocity === 93 && note.duration_tick === resized.durationTick)).toBe(true);
});

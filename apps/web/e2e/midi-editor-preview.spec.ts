import { expect, test } from "@playwright/test";

const API = "http://127.0.0.1:8000/api/v1";

function withoutRequestId<T extends Record<string, unknown>>(value: T): Omit<T, "request_id"> {
  const { request_id: _requestId, ...rest } = value;
  return rest;
}

test("T34.7 draft preview, transport, seek, loop and state boundary", async ({ page, request }) => {
  const generated = await request.post(`${API}/songs/generate`, {
    data: { prompt: "生成一段带 Bass、Melody 和 Drums 的电子配乐，96 BPM" },
  });
  expect(generated.ok()).toBeTruthy();
  const songId = (await generated.json()).song_id as string;
  expect((await request.post(`${API}/songs/${songId}/midi/generate`)).ok()).toBeTruthy();

  const initialDocResponse = await request.get(`${API}/songs/${songId}/midi/editor`);
  const initialDoc = await initialDocResponse.json() as {
    version_id: string;
    tracks: Array<{ id: string; notes: Array<{ id: string; start_tick: number }> }>;
  };
  const bassSaved = initialDoc.tracks.find((track) => track.id.toLowerCase().includes("bass"));
  expect(bassSaved?.notes.length).toBeGreaterThan(0);
  const initialAssets = withoutRequestId(await (await request.get(`${API}/songs/${songId}/assets`)).json());
  const initialMidi = await (await request.get(`${API}/songs/${songId}/midi/download`)).body();

  const mutations: string[] = [];
  const previewPayloads: Array<{ scope: string; tracks: Array<{ track_id: string; notes: Array<{ id: string; start_tick: number }> }> }> = [];
  page.on("request", (req) => {
    const url = req.url();
    if (req.method() !== "GET") mutations.push(`${req.method()} ${url}`);
    if (req.method() === "POST" && /\/midi\/preview$/.test(url)) {
      previewPayloads.push(req.postDataJSON());
    }
  });

  await page.goto(`/projects/${songId}`);
  const editor = page.locator(".midi-editor");
  await expect(editor).toBeVisible({ timeout: 30_000 });
  const bassOption = editor.getByRole("option", { name: /bass/i }).first();
  await bassOption.click();

  // Move one Bass note without Save.
  const firstBassNote = editor.locator("[data-note-id]").first();
  await firstBassNote.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const startX = rect.left + Math.min(10, Math.max(2, rect.width / 2));
    const startY = rect.top + Math.max(2, rect.height / 2);
    const init = { bubbles: true, pointerId: 17, pointerType: "mouse", isPrimary: true };
    element.dispatchEvent(new PointerEvent("pointerdown", { ...init, buttons: 1, clientX: startX, clientY: startY }));
    element.dispatchEvent(new PointerEvent("pointermove", { ...init, buttons: 1, clientX: startX + 90, clientY: startY }));
    element.dispatchEvent(new PointerEvent("pointerup", { ...init, buttons: 0, clientX: startX + 90, clientY: startY }));
  });
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();

  // Current Track Preview must send the moved Bass draft only.
  const currentPreview = page.waitForResponse(
    (response) => response.request().method() === "POST" && /\/midi\/preview$/.test(response.url()),
  );
  await editor.getByRole("button", { name: /Play/ }).click();
  expect((await currentPreview).ok()).toBeTruthy();
  await expect(editor.getByRole("button", { name: /Stop/ })).toBeEnabled({ timeout: 30_000 });
  expect(previewPayloads[0].scope).toBe("current_track");
  expect(previewPayloads[0].tracks).toHaveLength(1);
  expect(previewPayloads[0].tracks[0].track_id).toBe(bassSaved!.id);
  const movedStart = previewPayloads[0].tracks[0].notes.find((note) => note.id === bassSaved!.notes[0].id)?.start_tick;
  expect(movedStart).not.toBe(bassSaved!.notes[0].start_tick);

  const firstCleanup = page.waitForRequest(
    (req) => req.method() === "DELETE" && req.url().includes("/midi/preview/"),
  );
  await editor.getByRole("button", { name: /Stop/ }).click();
  await firstCleanup;
  await expect(editor.getByText(/未保存修改/).first()).toBeVisible();

  // Seek remains canonical under the current zoom/scroll geometry.
  const timeline = editor.getByRole("slider", { name: /MIDI 时间轴/ });
  const beforeSeek = Number(await timeline.getAttribute("aria-valuenow"));
  await timeline.click({ position: { x: 420, y: 14 } });
  const afterSeek = Number(await timeline.getAttribute("aria-valuenow"));
  expect(afterSeek).toBeGreaterThan(beforeSeek);

  // Loop uses simple bar inputs and the same Draft snapshot.
  await editor.getByLabel("Loop Start bar").fill("1");
  await editor.getByLabel("Loop End bar").fill("3");
  await editor.getByLabel("Loop 开关").check();
  await expect(editor.getByTestId("timeline-loop-region")).toBeVisible();
  const loopPreview = page.waitForResponse(
    (response) => response.request().method() === "POST" && /\/midi\/preview$/.test(response.url()),
  );
  await editor.getByRole("button", { name: /Play/ }).click();
  expect((await loopPreview).ok()).toBeTruthy();
  await expect(editor.getByRole("button", { name: /Stop/ })).toBeEnabled({ timeout: 30_000 });
  await editor.getByRole("button", { name: /Stop/ }).click();

  // Locked tracks remain previewable; All Tracks merges untouched tracks + Bass Draft.
  await editor.getByRole("button", { name: /编辑/ }).click();
  await editor.getByLabel("Loop 开关").uncheck();
  await editor.getByLabel("Preview 范围").selectOption("all_tracks");
  const allPreview = page.waitForResponse(
    (response) => response.request().method() === "POST" && /\/midi\/preview$/.test(response.url()),
  );
  await editor.getByRole("button", { name: /Play/ }).click();
  expect((await allPreview).ok()).toBeTruthy();
  await expect(editor.getByRole("button", { name: /Stop/ })).toBeEnabled({ timeout: 30_000 });
  const allPayload = previewPayloads.at(-1)!;
  expect(allPayload.scope).toBe("all_tracks");
  expect(allPayload.tracks).toHaveLength(initialDoc.tracks.length);
  const allBass = allPayload.tracks.find((track) => track.track_id === bassSaved!.id)!;
  expect(allBass.notes.find((note) => note.id === bassSaved!.notes[0].id)?.start_tick).toBe(movedStart);
  await editor.getByRole("button", { name: /Stop/ }).click();

  // Network/state boundary: no Save, Version creation or formal WAV render.
  const forbidden = mutations.filter((entry) =>
    entry.includes("/midi/edit") || entry.includes("/audio/render") || entry.includes("/versions"),
  );
  expect(forbidden).toEqual([]);
  const finalDoc = await (await request.get(`${API}/songs/${songId}/midi/editor`)).json();
  const finalAssets = withoutRequestId(await (await request.get(`${API}/songs/${songId}/assets`)).json());
  const finalMidi = await (await request.get(`${API}/songs/${songId}/midi/download`)).body();
  expect(finalDoc.version_id).toBe(initialDoc.version_id);
  expect(finalAssets.current_version).toEqual(initialAssets.current_version);
  expect(finalAssets.has_midi).toBe(initialAssets.has_midi);
  expect(finalAssets.midi).toEqual(initialAssets.midi);
  expect(finalAssets.has_audio).toBe(initialAssets.has_audio);
  expect(finalAssets.audio).toEqual(initialAssets.audio);
  expect(finalMidi.equals(initialMidi)).toBe(true);
});

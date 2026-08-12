import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type GeneratedProject = {
  song_id: string;
  music_spec: {
    tonality: { key: string; mode: string; scale: string | null };
    meter: { numerator: number; denominator: number };
    form: Array<{ id: string; name: string; start_bar: number; bars: number }>;
    harmony: Array<{ section: string; progression: string[] }>;
  };
};

type MidiEditorDocumentResponse = {
  version_id: string;
  tracks: Array<{
    id: string;
    channel: number;
    notes: Array<{
      id: string;
      pitch: number;
      start_tick: number;
      duration_tick: number;
      velocity: number;
      channel: number;
    }>;
  }>;
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function createMidiProject(request: APIRequestContext, prompt: string): Promise<GeneratedProject> {
  const generated = await request.post(`${API}/songs/generate`, { data: { prompt } });
  expect(generated.ok()).toBeTruthy();
  const project = await generated.json() as GeneratedProject;
  expect((await request.post(`${API}/songs/${project.song_id}/midi/generate`)).ok()).toBeTruthy();
  await expect.poll(async () => {
    const response = await request.get(`${API}/songs/${project.song_id}/assets`);
    return response.ok() && Boolean((await response.json()).has_midi);
  }, { timeout: 30_000 }).toBe(true);
  return project;
}

async function openEditor(page: Page, songId: string) {
  await page.goto(`/projects/${songId}`);
  const editor = page.locator(".midi-editor:visible").first();
  // createMidiProject already proves has_midi=true. Never regenerate here: a slow
  // workspace load must not overwrite the canonical MIDI prepared by the test.
  await expect(editor).toBeVisible({ timeout: 30_000 });
  return editor;
}

test("T34.9 real MusicSpec overlays, drum semantics, isolation and read-only boundary", async ({ page, request }) => {
  const projectA = await createMidiProject(request, "欢快明亮的电子配乐，带 Melody、Bass 和 Drums");
  const projectB = await createMidiProject(request, "忧郁雨夜的慢速配乐，带 Melody、Bass 和 Drums");
  // Establish a real monophonic Bass baseline before observing the read-only overlay boundary.
  // The page can then prove Draft overlap warning -> Undo without relying on generated Bass density.
  const initialDocumentA = await (await request.get(`${API}/songs/${projectA.song_id}/midi/editor`)).json() as MidiEditorDocumentResponse;
  const generatedBass = initialDocumentA.tracks.find((track) => /bass/i.test(track.id));
  expect(generatedBass?.notes.length).toBeGreaterThan(0);
  const bassSeed = generatedBass!.notes[0];
  const baselineResponse = await request.post(`${API}/songs/${projectA.song_id}/midi/edit`, {
    data: {
      track_id: generatedBass!.id,
      base_version_id: initialDocumentA.version_id,
      notes: [{
        ...bassSeed,
        start_tick: 0,
        duration_tick: 960,
        velocity: 90,
        channel: generatedBass!.channel,
      }],
    },
  });
  expect(baselineResponse.ok()).toBeTruthy();
  await expect.poll(async () => {
    const response = await request.get(`${API}/songs/${projectA.song_id}/midi/editor`);
    if (!response.ok()) return -1;
    const document = await response.json() as MidiEditorDocumentResponse;
    return document.tracks.find((track) => track.id === generatedBass!.id)?.notes.length ?? -1;
  }, { timeout: 30_000 }).toBe(1);
  const assetsBefore = await (await request.get(`${API}/songs/${projectA.song_id}/assets`)).json() as {
    current_version: { version_id: string; version_number: number };
  };
  let manualSaveRequests = 0;
  page.on("request", (outgoing) => {
    if (outgoing.method() === "POST" && /\/midi\/edit$/.test(outgoing.url())) manualSaveRequests += 1;
  });

  const editorA = await openEditor(page, projectA.song_id);
  await expect(editorA.getByRole("button", { name: "Scale ✓" })).toBeVisible();
  await expect(editorA.getByRole("button", { name: "Chords ✓" })).toBeVisible();
  await expect(editorA.getByRole("button", { name: "Sections ✓" })).toBeVisible();
  const scaleA = editorA.locator(".midi-editor__footer span").filter({ hasText: /^Scale:/ });
  await expect(scaleA).toContainText(projectA.music_spec.tonality.key);
  const scaleAText = (await scaleA.textContent())?.trim() ?? "";
  await expect(editorA.locator("[data-testid='section-overlay'] [data-section-id]")).toHaveCount(projectA.music_spec.form.length);
  const targetSection = projectA.music_spec.form.find((section) => section.id === "verse") ?? projectA.music_spec.form[0];
  const perBar = Math.round(480 * 4 / projectA.music_spec.meter.denominator) * projectA.music_spec.meter.numerator;
  await expect(editorA.locator(`[data-section-id='${targetSection.id}']`)).toHaveAttribute(
    "data-start-tick",
    String((targetSection.start_bar - 1) * perBar),
  );
  await expect(editorA.locator("[data-testid='chord-overlay'] [data-chord]").first()).toHaveAttribute("data-start-tick", "0");

  await editorA.getByRole("button", { name: "Sections ✓" }).click();
  await expect(editorA.locator("[data-testid='section-overlay']")).toHaveCount(0);
  await editorA.getByRole("button", { name: "Sections" }).click();
  await expect(editorA.locator("[data-testid='section-overlay']")).toBeVisible();

  await editorA.getByRole("option", { name: /drums/i }).first().click();
  for (const label of ["Kick", "Snare", "Closed Hat", "Open Hat", "Crash", "Ride"]) {
    await expect(editorA.getByText(label, { exact: true })).toBeVisible();
  }

  await editorA.getByRole("option", { name: /bass/i }).first().click();
  await expect(editorA.getByText(/Bass 轨检测到/)).toHaveCount(0);
  const bassRoll = editorA.locator(".midi-editor__grid");
  await bassRoll.dblclick({ position: { x: 20, y: 20 } });
  await expect(editorA.getByText(/Bass 轨检测到 1 处同时发声/)).toBeVisible();
  await editorA.getByRole("button", { name: "Undo" }).click();
  await expect(editorA.getByText(/Bass 轨检测到/)).toHaveCount(0);
  await expect(editorA.getByText(/未保存修改/)).toHaveCount(0);

  const assetsAfterToggle = await (await request.get(`${API}/songs/${projectA.song_id}/assets`)).json() as {
    current_version: { version_id: string; version_number: number };
  };
  expect(assetsAfterToggle.current_version).toEqual(assetsBefore.current_version);
  expect(manualSaveRequests).toBe(0);

  // A manual Note edit still uses the existing Save contract and must not back-write MusicSpec.
  await editorA.locator("[data-note-id]").first().click();
  await editorA.getByLabel("Velocity 力度").fill("77");
  await editorA.getByRole("button", { name: "保存 MIDI 修改" }).click();
  await expect(editorA.getByText(`Version: v${assetsBefore.current_version.version_number + 1}`)).toBeVisible({ timeout: 60_000 });
  expect(manualSaveRequests).toBe(1);
  const assetsAfterSave = await (await request.get(`${API}/songs/${projectA.song_id}/assets`)).json() as {
    current_version: { version_id: string; version_number: number };
  };
  expect(assetsAfterSave.current_version.version_number).toBe(assetsBefore.current_version.version_number + 1);
  const projectAAfterSave = await (await request.get(`${API}/songs/${projectA.song_id}`)).json() as GeneratedProject;
  expect(projectAAfterSave.music_spec).toEqual(projectA.music_spec);

  const editorB = await openEditor(page, projectB.song_id);
  const scaleB = editorB.locator(".midi-editor__footer span").filter({ hasText: /^Scale:/ });
  await expect(scaleB).toContainText(projectB.music_spec.tonality.key);
  const scaleBText = (await scaleB.textContent())?.trim() ?? "";
  expect(scaleBText).not.toBe(scaleAText);
  await expect(editorB.locator(".midi-editor__footer span").filter({ hasText: new RegExp(`^${escapeRegExp(scaleAText)}$`) })).toHaveCount(0);
  const firstChordB = projectB.music_spec.harmony[0].progression[0];
  await expect(
    editorB.locator(".midi-editor__chord-marker").filter({ hasText: new RegExp(`^${escapeRegExp(firstChordB)}$`) }).first(),
  ).toBeVisible();
  expect(manualSaveRequests).toBe(1);
});

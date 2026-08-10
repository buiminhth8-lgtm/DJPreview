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
  const editor = page.locator(".midi-editor");
  await page.waitForTimeout(500);
  if (!(await editor.isVisible())) {
    await page.getByRole("button", { name: "生成 MIDI" }).first().click();
  }
  await expect(editor).toBeVisible({ timeout: 30_000 });
  return editor;
}

test("T34.9 real MusicSpec overlays, drum semantics, isolation and read-only boundary", async ({ page, request }) => {
  const projectA = await createMidiProject(request, "欢快明亮的电子配乐，带 Melody、Bass 和 Drums");
  const projectB = await createMidiProject(request, "忧郁雨夜的慢速配乐，带 Melody、Bass 和 Drums");
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

  const assetsAfterToggle = await (await request.get(`${API}/songs/${projectA.song_id}/assets`)).json() as {
    current_version: { version_id: string; version_number: number };
  };
  expect(assetsAfterToggle.current_version).toEqual(assetsBefore.current_version);
  expect(manualSaveRequests).toBe(0);

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
  expect(manualSaveRequests).toBe(0);
});

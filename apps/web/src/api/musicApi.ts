export interface TempoSpec {
  bpm: number;
  feel: string | null;
}

export interface MeterSpec {
  numerator: number;
  denominator: number;
}

export interface TonalitySpec {
  key: string;
  mode: string;
  scale: string | null;
}

export interface LengthSpec {
  bars: number;
}

export interface SectionSpec {
  id: string;
  name: string;
  start_bar: number;
  bars: number;
  energy: number;
}

export interface HarmonySectionSpec {
  section: string;
  progression: string[];
}

export interface TrackSpec {
  id: string;
  role: string;
  instrument: string;
  pattern: string | null;
  register: string | null;
  velocity: number;
  enabled_sections: string[] | null;
}

export interface MusicSpec {
  version: string;
  title: string;
  seed: number;
  language: string;
  prompt: string;
  tempo: TempoSpec;
  meter: MeterSpec;
  tonality: TonalitySpec;
  length: LengthSpec;
  style: string[];
  mood: string[];
  form: SectionSpec[];
  harmony: HarmonySectionSpec[];
  tracks: TrackSpec[];
  notes: string | null;
}

export interface GenerateSongResponse {
  song_id: string;
  music_spec: MusicSpec;
  style_template: StyleTemplateSpec | null;
}

export interface MidiSummary {
  tracks: number;
  bars: number;
  bpm: number;
}

export interface GenerateMidiResponse {
  song_id: string;
  midi_file: string;
  download_url: string;
  summary: MidiSummary;
}

export interface AudioMetadata {
  audio_file: string;
  renderer: string;
  sample_rate: number;
  duration_seconds: number | null;
  file_size: number;
  generated_at: string | null;
  generator_version: string | null;
  warnings: string[];
}

export interface RenderAudioResponse {
  song_id: string;
  audio_file: string;
  stream_url: string;
  download_url: string;
  metadata: AudioMetadata;
}

export interface VersionInfo {
  version_id: string;
  version_number: number;
  created_at: string;
  instruction: string | null;
  parent_version_id: string | null;
}

export interface AssetsResponse {
  song_id: string;
  has_music_spec: boolean;
  has_midi: boolean;
  has_audio: boolean;
  midi: { download_url: string } | null;
  audio: {
    stream_url: string;
    download_url: string;
    metadata: AudioMetadata | null;
  } | null;
  current_version: VersionInfo | null;
}

export interface VersionsResponse {
  song_id: string;
  current_version_id: string;
  versions: VersionInfo[];
}

export interface DiffItem {
  field: string;
  old: unknown;
  new: unknown;
}

export interface EditSongResponse {
  song_id: string;
  version_id: string;
  edit_spec: {
    version: string;
    instruction: string;
    target: { section: string | null; track: string | null; scope: string };
    preserve: string[];
    operations: Array<{ type: string; amount: number | null; value: unknown; params: unknown }>;
  };
  diff: DiffItem[];
  music_spec: MusicSpec;
  assets: AssetsResponse;
}

export interface RestoreVersionResponse {
  song_id: string;
  version_id: string;
  music_spec: MusicSpec;
  assets: AssetsResponse;
}

export interface VersionDetailResponse extends VersionInfo {
  music_spec: MusicSpec;
  edit_spec: {
    version: string;
    instruction: string;
    target: { section: string | null; track: string | null; scope: string };
    preserve: string[];
    operations: Array<{ type: string; amount: number | null; value: unknown; params: unknown }>;
  } | null;
  is_current: boolean;
  assets: AssetsResponse;
}

export interface VersionDiffResponse {
  song_id: string;
  version_id: string;
  version_number: number;
  is_current: boolean;
  base_version_id: string;
  base_version_number: number;
  diff: DiffItem[];
  music_spec: MusicSpec;
  assets: AssetsResponse;
}

export interface TrackMixSpec {
  track_id: string;
  role: string | null;
  volume: number;
  pan: number;
  mute: boolean;
  solo: boolean;
  enabled: boolean;
  velocity_scale: number;
  program: number | null;
  instrument: string | null;
}

export interface MixSpec {
  version: string;
  song_id: string | null;
  version_id: string | null;
  master_volume: number;
  tracks: TrackMixSpec[];
  notes: string | null;
}

export interface TrackMixPatch {
  track_id: string;
  volume?: number;
  pan?: number;
  mute?: boolean;
  solo?: boolean;
  enabled?: boolean;
  velocity_scale?: number;
}

export interface MixResponse {
  song_id: string;
  version_id: string | null;
  mix_spec: MixSpec;
}

export interface ApplyMixResponse {
  song_id: string;
  mix_spec: MixSpec;
  assets: AssetsResponse;
  warnings: string[];
}

export interface PianoRollData {
  ticks_per_beat: number;
  bpm: number | null;
  beats_per_bar: number;
  total_bars: number;
  total_notes: number;
  truncated: boolean;
  sections: Array<{ id: string; name: string; start_bar: number; bars: number; energy: number }>;
  tracks: Array<{
    track_index: number;
    track_name: string | null;
    role: string | null;
    min_pitch: number | null;
    max_pitch: number | null;
    notes: Array<{
      pitch: number;
      pitch_name: string;
      start_beat: number;
      duration_beats: number;
      velocity: number;
      is_drum: boolean;
    }>;
  }>;
}

export interface QualityIssue {
  severity: string;
  category: string;
  message: string;
  target: Record<string, unknown> | null;
  suggestion: string | null;
}

export interface QualityReport {
  score: number;
  level: string;
  issues: QualityIssue[];
  suggestions: string[];
  summary: string;
}

export interface OptimizeResponse {
  song_id: string;
  version_id: string;
  music_spec: MusicSpec;
  quality_report_before: QualityReport;
  optimize_report: { changes: string[]; warnings: string[] };
  assets: AssetsResponse;
}

export interface StemExportResponse {
  song_id: string;
  stems: Array<{ track_id: string; midi_download_url: string; wav_download_url: string }>;
  zip_download_url: string;
  warnings: string[];
}

// ---------- 第六阶段 ----------

export interface StyleTemplateSpec {
  id: string;
  name: string;
  description: string;
  tags: string[];
  default_tempo: number | null;
  tempo_range: [number, number] | null;
  preferred_keys: string[];
  preferred_modes: string[];
  preferred_scales: string[];
  default_meter: string;
  default_length_bars: number;
  default_form: Array<Record<string, unknown>>;
  default_tracks: Array<Record<string, unknown>>;
  harmony_presets: string[][];
  rhythm_presets: string[];
  melody_profile: Record<string, unknown>;
  arrangement_curve: Record<string, unknown>;
  mix_hints: Record<string, unknown> | null;
  notes: string | null;
}

export interface ReferenceMidiAnalysis {
  file_name: string;
  ticks_per_beat: number;
  bpm: number | null;
  estimated_bars: number;
  track_count: number;
  note_count: number;
  pitch_range: { min: number | null; max: number | null };
  density: { notes_per_bar: number; avg_velocity: number; max_velocity: number };
  rhythm_profile: { has_drums: boolean; avg_duration_beats: number };
  energy_curve: Array<{ segment_index: number; start_bar: number; note_count: number; energy: number }>;
  track_summaries: Array<Record<string, unknown>>;
  possible_roles: string[];
  suggested_style_tags: string[];
  suggested_tempo_range: [number, number] | null;
  suggested_tracks: Array<{ role: string; instrument: string }>;
  warnings: string[];
}

export interface GenerateFromReferenceResponse {
  song_id: string;
  music_spec: MusicSpec;
  reference_analysis: ReferenceMidiAnalysis;
  style_template: StyleTemplateSpec | null;
}

export interface RegenerationRequest {
  scope: "section" | "track" | "section_track" | "overall";
  section_id?: string | null;
  track_id?: string | null;
  instruction?: string | null;
  keep_harmony: boolean;
  keep_melody: boolean;
  keep_rhythm: boolean;
  variation_strength: number;
  seed_offset: number;
  auto_render: boolean;
}

export interface RegenerationResult {
  song_id: string;
  version_id: string;
  parent_version_id: string;
  music_spec: MusicSpec;
  changed_targets: Array<Record<string, unknown>>;
  warnings: string[];
  assets: AssetsResponse;
}

export interface EvalCase {
  id: string;
  prompt: string;
  style_template_id: string | null;
  expected_traits: Record<string, unknown>;
  notes: string | null;
}

export interface EvalResult {
  case_id: string;
  song_id: string | null;
  score: number;
  quality_score: number;
  trait_matches: Record<string, boolean>;
  warnings: string[];
  errors: string[];
}

export interface EvalReport {
  created_at: string;
  total_cases: number;
  passed_cases: number;
  average_score: number;
  results: EvalResult[];
  summary: string;
}

export interface ProjectImportResponse {
  song_id: string;
  imported: boolean;
  summary: Record<string, unknown>;
}

// 后端 API 地址可通过 VITE_API_BASE_URL 环境变量配置，默认 http://localhost:8000
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function handleError(response: Response): Promise<never> {
  const text = await response.text();
  let detail = text || "未知错误";
  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (body && typeof body === "object" && body.detail !== undefined) {
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    }
  } catch {
    // 非 JSON 响应，保留原文
  }
  throw new Error(`请求失败（HTTP ${response.status}）：${detail}`);
}

async function requestJson<T>(url: string, method: string, payload?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    method,
    headers: payload !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });
  if (!response.ok) {
    return handleError(response);
  }
  return (await response.json()) as T;
}

async function requestForm<T>(url: string, form: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    return handleError(response);
  }
  return (await response.json()) as T;
}

export function generateMusicSpec(
  prompt: string,
  styleTemplateId?: string | null,
  styleStrength = 0.7,
): Promise<GenerateSongResponse> {
  return requestJson("/api/v1/songs/generate", "POST", {
    prompt,
    ...(styleTemplateId ? { style_template_id: styleTemplateId, style_strength: styleStrength } : {}),
  });
}

export function getSong(songId: string): Promise<{ song_id: string; music_spec: MusicSpec }> {
  return requestJson(`/api/v1/songs/${songId}`, "GET");
}

export function generateMidi(songId: string): Promise<GenerateMidiResponse> {
  return requestJson(`/api/v1/songs/${songId}/midi/generate`, "POST");
}

export function renderAudio(songId: string): Promise<RenderAudioResponse> {
  return requestJson(`/api/v1/songs/${songId}/audio/render`, "POST");
}

export function getAssets(songId: string): Promise<AssetsResponse> {
  return requestJson(`/api/v1/songs/${songId}/assets`, "GET");
}

export function editSong(songId: string, instruction: string): Promise<EditSongResponse> {
  return requestJson(`/api/v1/songs/${songId}/edit`, "POST", { instruction });
}

export function getVersions(songId: string): Promise<VersionsResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions`, "GET");
}

export function restoreVersion(songId: string, versionId: string): Promise<RestoreVersionResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions/${versionId}/restore`, "POST");
}

export function getVersion(songId: string, versionId: string): Promise<VersionDetailResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions/${versionId}`, "GET");
}

export function getVersionDiff(songId: string, versionId: string): Promise<VersionDiffResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions/${versionId}/diff`, "GET");
}

export function getMix(songId: string): Promise<MixResponse> {
  return requestJson(`/api/v1/songs/${songId}/mix`, "GET");
}

export function updateMix(
  songId: string,
  patch: { master_volume?: number; tracks: TrackMixPatch[] },
  apply: boolean,
): Promise<{ song_id: string; version_id: string | null; mix_spec: MixSpec; assets: AssetsResponse | null }> {
  return requestJson(`/api/v1/songs/${songId}/mix?apply=${apply}`, "PATCH", patch);
}

export function applyMix(songId: string): Promise<ApplyMixResponse> {
  return requestJson(`/api/v1/songs/${songId}/mix/apply`, "POST");
}

export function getPianoRoll(songId: string, trackId?: string, maxNotes = 5000): Promise<PianoRollData> {
  const params = new URLSearchParams({ max_notes: String(maxNotes) });
  if (trackId) params.set("track_id", trackId);
  return requestJson(`/api/v1/songs/${songId}/piano-roll?${params.toString()}`, "GET");
}

export function checkQuality(songId: string): Promise<QualityReport> {
  return requestJson(`/api/v1/songs/${songId}/quality/check`, "POST");
}

export function getQualityReport(songId: string): Promise<QualityReport> {
  return requestJson(`/api/v1/songs/${songId}/quality/report`, "GET");
}

export function optimizeArrangement(songId: string, autoRender = true): Promise<OptimizeResponse> {
  return requestJson(`/api/v1/songs/${songId}/quality/optimize`, "POST", { auto_render: autoRender });
}

export function exportStems(songId: string): Promise<StemExportResponse> {
  return requestJson(`/api/v1/songs/${songId}/stems/export`, "POST");
}

// ---------- 第六阶段 API ----------

export function listStyles(): Promise<StyleTemplateSpec[]> {
  return requestJson("/api/v1/styles", "GET");
}

export function getStyle(id: string): Promise<StyleTemplateSpec> {
  return requestJson(`/api/v1/styles/${id}`, "GET");
}

export function analyzeReferenceMidi(file: File): Promise<ReferenceMidiAnalysis> {
  const form = new FormData();
  form.append("file", file);
  return requestForm("/api/v1/reference/analyze", form);
}

export function generateFromReference(
  file: File,
  prompt: string,
  styleTemplateId?: string | null,
  styleStrength = 0.7,
): Promise<GenerateFromReferenceResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("prompt", prompt);
  if (styleTemplateId) {
    form.append("style_template_id", styleTemplateId);
    form.append("style_strength", String(styleStrength));
  }
  return requestForm("/api/v1/songs/generate-from-reference", form);
}

export function regenerateSong(songId: string, request: RegenerationRequest): Promise<RegenerationResult> {
  return requestJson(`/api/v1/songs/${songId}/regenerate`, "POST", request);
}

export function exportProjectUrl(songId: string): string {
  return `${API_BASE_URL}/api/v1/songs/${songId}/project/export`;
}

export function importProject(file: File): Promise<ProjectImportResponse> {
  const form = new FormData();
  form.append("file", file);
  return requestForm("/api/v1/projects/import", form);
}

export function listEvalCases(): Promise<EvalCase[]> {
  return requestJson("/api/v1/evaluation/cases", "GET");
}

export function runEvaluation(caseIds: string[], renderAudio = false): Promise<EvalReport> {
  return requestJson("/api/v1/evaluation/run", "POST", { case_ids: caseIds, render_audio: renderAudio });
}

export function resolveUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

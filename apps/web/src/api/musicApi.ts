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

// ---------- 第五阶段 ----------

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

export function generateMusicSpec(prompt: string): Promise<GenerateSongResponse> {
  return requestJson("/api/v1/songs/generate", "POST", { prompt });
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

export function resolveUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

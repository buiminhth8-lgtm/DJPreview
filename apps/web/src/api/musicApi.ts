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

// 后端 API 地址可通过 VITE_API_BASE_URL 环境变量配置，默认 http://localhost:8000
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function handleError(response: Response): Promise<never> {
  // 先读取文本，再尝试解析 JSON，避免 response.json() 失败后 body 被消费
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

async function postJson<T>(url: string, payload?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    method: "POST",
    headers: payload ? { "Content-Type": "application/json" } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  if (!response.ok) {
    return handleError(response);
  }
  return (await response.json()) as T;
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`);
  if (!response.ok) {
    return handleError(response);
  }
  return (await response.json()) as T;
}

export function generateMusicSpec(prompt: string): Promise<GenerateSongResponse> {
  return postJson("/api/v1/songs/generate", { prompt });
}

export function generateMidi(songId: string): Promise<GenerateMidiResponse> {
  return postJson(`/api/v1/songs/${songId}/midi/generate`);
}

export function renderAudio(songId: string): Promise<RenderAudioResponse> {
  return postJson(`/api/v1/songs/${songId}/audio/render`);
}

export function getAssets(songId: string): Promise<AssetsResponse> {
  return getJson(`/api/v1/songs/${songId}/assets`);
}

export function editSong(songId: string, instruction: string): Promise<EditSongResponse> {
  return postJson(`/api/v1/songs/${songId}/edit`, { instruction });
}

export function getVersions(songId: string): Promise<VersionsResponse> {
  return getJson(`/api/v1/songs/${songId}/versions`);
}

export function restoreVersion(songId: string, versionId: string): Promise<RestoreVersionResponse> {
  return postJson(`/api/v1/songs/${songId}/versions/${versionId}/restore`);
}

export function resolveUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

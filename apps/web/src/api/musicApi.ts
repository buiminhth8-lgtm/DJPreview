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

// 后端 API 地址可通过 VITE_API_BASE_URL 环境变量配置，默认 http://localhost:8000
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function handleError(response: Response): Promise<never> {
  let detail = "";
  try {
    const body = await response.json();
    detail = body?.detail ?? JSON.stringify(body);
  } catch {
    detail = await response.text();
  }
  throw new Error(`请求失败（HTTP ${response.status}）：${detail}`);
}

export async function generateMusicSpec(prompt: string): Promise<GenerateSongResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/songs/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!response.ok) {
    return handleError(response);
  }
  return (await response.json()) as GenerateSongResponse;
}

export async function generateMidi(songId: string): Promise<GenerateMidiResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/songs/${songId}/midi/generate`, {
    method: "POST",
  });
  if (!response.ok) {
    return handleError(response);
  }
  return (await response.json()) as GenerateMidiResponse;
}

// 前端 API 共享类型（T23：从 musicApi.ts 拆分而来）。

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

export interface ValidationIssue {
  code: string;
  message: string;
  path: string | null;
  details: Record<string, unknown>;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface SongAssets {
  has_midi?: boolean;
  has_audio?: boolean;
  has_mix?: boolean;
  has_quality_report?: boolean;
  has_stems?: boolean;
  midi_download_url?: string | null;
  audio_stream_url?: string | null;
  audio_download_url?: string | null;
  [key: string]: unknown;
}

export interface SongResponse {
  song_id: string;
  music_spec: MusicSpec;
  assets?: SongAssets;
  current_version_id?: string | null;
}

export interface EditSongRequest {
  instruction: string;
  auto_render?: boolean;
}

export interface GenerateSongRequest {
  prompt: string;
  style_template_id?: string | null;
  style_strength?: number;
}

export interface WarningItem {
  code: string;
  message: string;
  stage?: string;
  severity?: string;
}

export interface GenerationDebug {
  provider?: string | null;
  model?: string | null;
  llm_duration_ms?: number | null;
  parse_duration_ms?: number | null;
  validation_warning_count?: number;
  request_id?: string | null;
}

export interface GenerateSongResponse {
  song_id: string;
  music_spec: MusicSpec;
  style_template: StyleTemplateSpec | null;
  validation?: ValidationResult | null;
  request_id?: string | null;
  warnings?: WarningItem[];
  debug?: GenerationDebug | null;
}

export interface GenerateWithMidiResponse {
  song_id: string;
  music_spec: MusicSpec;
  midi: MidiInfo;
  validation?: ValidationResult | null;
}

export interface GenerateWithAudioResponse {
  song_id: string;
  music_spec: MusicSpec;
  midi: MidiInfo;
  audio: RenderAudioResponse;
  validation?: ValidationResult | null;
}

export interface MidiSummary {
  tracks: number;
  bars: number;
  bpm: number;
}

export interface MidiInfo {
  midi_file: string;
  download_url: string;
}

export interface GenerateMidiResponse {
  song_id: string;
  midi_file: string;
  download_url: string;
  summary: MidiSummary;
}

export type AudioRenderQuality = "preview" | "basic" | "soundfont" | "unknown";

export type FallbackReason =
  | "no_soundfont_selected"
  | "soundfont_file_missing"
  | "soundfont_not_found"
  | "fluidsynth_unavailable"
  | "fluidsynth_render_failed"
  | "renderer_not_configured"
  | "unknown";

export interface RendererWarning {
  code?: string;
  message?: string;
}

export interface FluidsynthStatus {
  available: boolean;
  binary?: string | null;
  version?: string | null;
  error?: string | null;
}

export interface AudioRenderMetadata {
  renderer?: string | null;
  rendererLabel?: string | null;
  quality?: AudioRenderQuality | null;
  isFallback?: boolean;
  fallbackReason?: FallbackReason | null;
  soundfontId?: string | null;
  soundfontName?: string | null;
  soundfontPath?: string | null;
  warnings?: Array<{ code?: string; message?: string }>;
}

export interface AudioMetadata {
  audio_file: string;
  renderer: string;
  renderer_label?: string | null;
  quality?: AudioRenderQuality | null;
  is_fallback?: boolean;
  fallback_reason?: FallbackReason | null;
  sample_rate: number;
  duration_seconds: number | null;
  file_size: number;
  generated_at: string | null;
  generator_version: string | null;
  warnings: string[];
  renderer_warnings?: RendererWarning[];
  soundfont_id?: string | null;
  soundfont_name?: string | null;
  soundfont_path?: string | null;
  fluidsynth?: FluidsynthStatus | null;
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
  has_mix: boolean;
  has_quality_report: boolean;
  has_stems: boolean;
  audio_needs_render?: boolean;
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
  auto_render: boolean;
  audio_rendered: boolean;
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

export interface RestoreSummary {
  restored: string[];
  removed: string[];
  missing_optional: string[];
}

export interface RestoreVersionResponse {
  song_id: string;
  version_id: string;
  restored_version_id: string;
  current_version_id: string;
  music_spec: MusicSpec;
  assets: AssetsResponse;
  restore_summary: RestoreSummary | null;
}

export interface VersionAssetInfo {
  has_midi: boolean;
  has_audio: boolean;
  midi_download_url: string | null;
  audio_stream_url: string | null;
  audio_download_url: string | null;
}

export interface VersionDetailResponse {
  song_id: string;
  version_id: string;
  is_current: boolean;
  metadata: {
    version_id: string;
    index: number;
    parent_version_id: string | null;
    created_at: string | null;
    prompt: string | null;
    edit_instruction: string | null;
    notes: string | null;
  };
  music_spec: MusicSpec;
  edit_spec: {
    version: string;
    instruction: string;
    target: { section: string | null; track: string | null; scope: string };
    preserve: string[];
    operations: Array<{ type: string; amount: number | null; value: unknown; params: unknown }>;
  } | null;
  diff: DiffItem[] | null;
  assets: VersionAssetInfo;
}

export interface VersionDiffResponse {
  song_id: string;
  version_id: string;
  parent_version_id: string | null;
  is_current: boolean;
  diff: DiffItem[] | null;
  metadata: {
    version_id: string;
    index: number;
    parent_version_id: string | null;
    created_at: string | null;
    prompt: string | null;
    edit_instruction: string | null;
    notes: string | null;
  };
  warnings: string[];
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
  song_id: string;
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
  music_spec: Record<string, unknown> | null;
  midi_path: string | null;
  quality_report: Record<string, unknown> | null;
  render_audio: boolean;
  audio_rendered: boolean;
  audio_path: string | null;
  audio_duration_seconds: number | null;
  renderer: string | null;
  render_error: string | null;
  warnings: string[];
  errors: string[];
}

export interface EvalReport {
  run_id: string;
  created_at: string;
  render_audio: boolean;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  average_score: number;
  audio_rendered_cases: number;
  audio_failed_cases: number;
  results: EvalResult[];
  warnings: string[];
  summary: string;
}

export interface ProjectImportResponse {
  song_id: string;
  imported: boolean;
  summary: Record<string, unknown>;
  source_song_id?: string | null;
  current_version_id?: string | null;
  version_count?: number;
  assets?: Record<string, unknown>;
  warnings?: string[];
}

// ---------- T29：SoundFont / 音源管理 ----------

export interface SoundFontInfo {
  id: string;
  name: string;
  path: string;
  format: string;
  size_bytes: number;
  is_default: boolean;
  tags: string[];
}

export interface SoundfontListResponse {
  soundfonts: SoundFontInfo[];
  default_soundfont_id: string | null;
}

export interface ProjectSoundfontRequest {
  soundfont_id: string;
  renderer?: string | null;
}

export interface ProjectSoundfontResponse {
  song_id: string;
  soundfont: {
    soundfont_id: string;
    soundfont_name: string | null;
    renderer: string;
  } | null;
  available: boolean;
  warning: string | null;
}

export interface SoundfontDiagnosticsFile {
  id: string | null;
  name: string | null;
  path: string | null;
  exists: boolean;
  readable: boolean;
  valid: boolean;
  format: string | null;
  size_bytes: number;
  error: string | null;
}

export interface SoundfontDiagnosticsResponse {
  soundfont_dirs: string[];
  soundfonts_found: number;
  soundfonts: SoundfontDiagnosticsFile[];
  fluidsynth: FluidsynthStatus;
  renderer_backends: {
    fallback: boolean;
    fluidsynth: boolean;
  };
}

// ---------- T30：异步渲染任务 ----------

export type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface RenderTask {
  task_id: string;
  song_id: string;
  task_type: string;
  status: TaskStatus;
  progress: number;
  message?: string | null;
  error?: string | null;
  result?: Record<string, unknown>;
  cancel_requested?: boolean;
  created_at: string;
  updated_at: string;
}

// ---------- 命名别名（保持与后端领域命名一致） ----------

export type VersionListResponse = VersionsResponse;
export type MidiGenerateResponse = GenerateMidiResponse;
export type AudioRenderResponse = RenderAudioResponse;
export type PianoRollResponse = PianoRollData;
export type QualityReportResponse = QualityReport;
export type ReferenceAnalyzeResponse = ReferenceMidiAnalysis;
export type EvaluationRunResponse = EvalReport;
export type ImportProjectResponse = ProjectImportResponse;
export type StyleTemplateResponse = StyleTemplateSpec;

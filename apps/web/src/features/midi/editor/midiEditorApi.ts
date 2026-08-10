// features/midi/editor/midiEditorApi.ts（T34.1）
// MIDI 编辑器读取 API：后端 snake_case → 前端 camelCase 边界归一化。

import { requestJson } from "../../../api/client";
import type { MidiEditorDocument, MidiEditorNote, MidiEditorTrack } from "./midiEditorTypes";

interface RawMidiEditorNote {
  id: string;
  pitch: number;
  start_tick: number;
  duration_tick: number;
  velocity: number;
  channel: number;
}

interface RawMidiEditorTrack {
  id: string;
  role: string | null;
  name: string;
  channel: number;
  instrument: string | null;
  is_drum: boolean;
  notes: RawMidiEditorNote[];
}

interface RawMidiEditorDocument {
  song_id: string;
  version_id: string | null;
  ppq: number;
  bpm: number | null;
  time_signature: [number, number];
  total_bars: number;
  tracks: RawMidiEditorTrack[];
}

function mapNote(raw: RawMidiEditorNote): MidiEditorNote {
  return {
    id: raw.id,
    pitch: raw.pitch,
    startTick: raw.start_tick,
    durationTick: raw.duration_tick,
    velocity: raw.velocity,
    channel: raw.channel,
  };
}

function mapTrack(raw: RawMidiEditorTrack): MidiEditorTrack {
  return {
    id: raw.id,
    role: raw.role,
    name: raw.name,
    channel: raw.channel,
    instrument: raw.instrument,
    isDrum: raw.is_drum,
    notes: raw.notes.map(mapNote),
  };
}

export function mapMidiEditorDocument(raw: RawMidiEditorDocument): MidiEditorDocument {
  return {
    songId: raw.song_id,
    versionId: raw.version_id,
    ppq: raw.ppq,
    bpm: raw.bpm,
    timeSignature: raw.time_signature,
    totalBars: raw.total_bars,
    tracks: raw.tracks.map(mapTrack),
  };
}

export function getMidiEditorDocument(
  songId: string,
  options?: { signal?: AbortSignal },
): Promise<MidiEditorDocument> {
  const encoded = encodeURIComponent(songId);
  return requestJson<RawMidiEditorDocument>(
    `/api/v1/songs/${encoded}/midi/editor`,
    "GET",
    undefined,
    options?.signal,
  ).then(mapMidiEditorDocument);
}

export interface SaveMidiEditorTrackInput {
  trackId: string;
  baseVersionId: string | null;
  notes: MidiEditorNote[];
}

export interface SaveMidiEditorTrackResult {
  songId: string;
  versionId: string;
  warnings: string[];
}

export function saveMidiEditorTrack(
  songId: string,
  input: SaveMidiEditorTrackInput,
  options?: { signal?: AbortSignal },
): Promise<SaveMidiEditorTrackResult> {
  const encoded = encodeURIComponent(songId);
  return requestJson<{
    song_id: string;
    version_id: string;
    warnings?: string[];
  }>(
    `/api/v1/songs/${encoded}/midi/edit`,
    "POST",
    {
      track_id: input.trackId,
      base_version_id: input.baseVersionId,
      notes: input.notes.map((n) => ({
        id: n.id,
        pitch: n.pitch,
        start_tick: n.startTick,
        duration_tick: n.durationTick,
        velocity: n.velocity,
        channel: n.channel,
      })),
    },
    options?.signal,
  ).then((data) => ({
    songId: data.song_id,
    versionId: data.version_id,
    warnings: data.warnings ?? [],
  }));
}

export type MidiPreviewScope = "current_track" | "all_tracks";

export interface MidiEditorPreviewTrackInput {
  trackId: string;
  notes: MidiEditorNote[];
}

export interface CreateMidiEditorPreviewInput {
  scope: MidiPreviewScope;
  tracks: MidiEditorPreviewTrackInput[];
}

export interface MidiEditorPreviewResult {
  token: string;
  streamUrl: string;
  cleanupUrl: string;
  durationSeconds: number | null;
  warnings: string[];
}

export function createMidiEditorPreview(
  songId: string,
  input: CreateMidiEditorPreviewInput,
  options?: { signal?: AbortSignal },
): Promise<MidiEditorPreviewResult> {
  const encoded = encodeURIComponent(songId);
  return requestJson<{
    token: string;
    stream_url: string;
    cleanup_url: string;
    duration_seconds: number | null;
    warnings?: string[];
  }>(
    `/api/v1/songs/${encoded}/midi/preview`,
    "POST",
    {
      scope: input.scope,
      tracks: input.tracks.map((track) => ({
        track_id: track.trackId,
        notes: track.notes.map((note) => ({
          id: note.id,
          pitch: note.pitch,
          start_tick: note.startTick,
          duration_tick: note.durationTick,
          velocity: note.velocity,
          channel: note.channel,
        })),
      })),
    },
    options?.signal,
  ).then((data) => ({
    token: data.token,
    streamUrl: data.stream_url,
    cleanupUrl: data.cleanup_url,
    durationSeconds: data.duration_seconds,
    warnings: data.warnings ?? [],
  }));
}

export async function deleteMidiEditorPreview(cleanupUrl: string): Promise<boolean> {
  const data = await requestJson<{ cleaned: boolean }>(cleanupUrl, "DELETE");
  return data.cleaned;
}

import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useAudioAssets } from "./useAudioAssets";
import * as audioApi from "../api/audioApi";

vi.mock("../api/audioApi", () => ({
  getAssets: vi.fn(),
  getAudioDownloadUrl: vi.fn(() => "/api/v1/songs/x/audio/download"),
  getMidiDownloadUrl: vi.fn(() => "/api/v1/songs/x/midi/download"),
  getStemsZipUrl: vi.fn(() => "/api/v1/songs/x/stems/download"),
  generateMidi: vi.fn(),
  renderAudio: vi.fn(),
  exportStems: vi.fn(),
  downloadMidi: vi.fn(),
  downloadAudio: vi.fn(),
  downloadStems: vi.fn(),
}));

describe("useAudioAssets stale state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (audioApi.getAssets as ReturnType<typeof vi.fn>).mockResolvedValue({
      song_id: "s1",
      has_music_spec: true,
      has_midi: false,
      has_audio: false,
    });
  });

  it("markAudioStale sets audioNeedsRender true, render success clears it", async () => {
    const { result } = renderHook(() => useAudioAssets("s1"));
    expect(result.current.audioNeedsRender).toBe(false);

    act(() => result.current.markAudioStale());
    expect(result.current.audioNeedsRender).toBe(true);

    // 渲染成功 → stale 清除 + metadata 刷新
    const renderResponse = {
      song_id: "s1",
      audio_file: "output.wav",
      stream_url: "/api/v1/songs/s1/audio/stream",
      download_url: "/api/v1/songs/s1/audio/download",
      metadata: {
        audio_file: "output.wav",
        renderer: "fluidsynth",
        is_fallback: false,
        sample_rate: 44100,
        duration_seconds: 10,
        file_size: 1000,
        generated_at: null,
        generator_version: null,
        warnings: [],
        soundfont_name: "GeneralUser-GS",
      },
    };
    (audioApi.renderAudio as ReturnType<typeof vi.fn>).mockResolvedValue(renderResponse);

    await act(async () => {
      await result.current.renderAudio();
    });
    expect(result.current.audioNeedsRender).toBe(false);
    expect(result.current.audioRenderMetadata?.renderer).toBe("fluidsynth");
    expect(result.current.audioRenderMetadata?.soundfontName).toBe("GeneralUser-GS");
  });

  it("selected vs rendered soundfont stays separated: render metadata is authoritative", async () => {
    const { result } = renderHook(() => useAudioAssets("s1"));
    // 模拟 assets 返回已渲染 metadata（rendered=GeneralUser-GS）
    (audioApi.getAssets as ReturnType<typeof vi.fn>).mockResolvedValue({
      song_id: "s1",
      has_music_spec: true,
      has_midi: true,
      has_audio: true,
      audio: {
        stream_url: "/stream",
        download_url: "/download",
        metadata: {
          audio_file: "output.wav",
          renderer: "fluidsynth",
          is_fallback: false,
          sample_rate: 44100,
          duration_seconds: 10,
          file_size: 1000,
          generated_at: null,
          generator_version: null,
          warnings: [],
          soundfont_name: "GeneralUser-GS",
        },
      },
    });
    await act(async () => {
      await result.current.refreshAssets();
    });
    // 选择新 SoundFont 只置 stale，不改 rendered metadata
    act(() => result.current.markAudioStale());
    expect(result.current.audioNeedsRender).toBe(true);
    expect(result.current.audioRenderMetadata?.soundfontName).toBe("GeneralUser-GS");
  });

  it("keeps WAV stale when re-render fails", async () => {
    const { result } = renderHook(() => useAudioAssets("s1"));
    act(() => result.current.markAudioStale());
    (audioApi.renderAudio as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("render failed"));

    await act(async () => {
      expect(await result.current.renderAudio()).toBeNull();
    });

    expect(result.current.audioNeedsRender).toBe(true);
  });

  it("can clear stale after authoritative restore assets are applied", () => {
    const { result } = renderHook(() => useAudioAssets("s1"));
    act(() => result.current.markAudioStale());
    expect(result.current.audioNeedsRender).toBe(true);
    act(() => result.current.clearAudioStale());
    expect(result.current.audioNeedsRender).toBe(false);
  });

  it("restores persisted stale state from a fresh assets response", async () => {
    (audioApi.getAssets as ReturnType<typeof vi.fn>).mockResolvedValue({
      song_id: "s1",
      has_music_spec: true,
      has_midi: true,
      has_audio: true,
      has_mix: false,
      has_quality_report: false,
      has_stems: false,
      audio_needs_render: true,
      midi: null,
      audio: null,
      current_version: null,
    });
    const { result } = renderHook(() => useAudioAssets("s1"));

    await act(async () => {
      await result.current.refreshAssets();
    });

    expect(result.current.audioNeedsRender).toBe(true);
  });
});

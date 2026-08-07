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
});

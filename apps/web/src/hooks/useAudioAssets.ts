// useAudioAssets：MIDI / WAV / stems / assets 状态与下载 URL。

import { useCallback, useState } from "react";

import {
  getAssets,
  getAudioDownloadUrl,
  getMidiDownloadUrl,
  getStemsZipUrl,
  generateMidi as generateMidiApi,
  renderAudio as renderAudioApi,
} from "../api/audioApi";
import { resolveUrl } from "../api/client";
import type { AssetsResponse, AudioMetadata, AudioRenderMetadata, GenerateMidiResponse, RenderAudioResponse } from "../api/types";
import { getErrorMessage } from "./error";

function toAudioRenderMetadata(metadata: AudioMetadata | null | undefined): AudioRenderMetadata | null {
  if (!metadata) return null;
  return {
    renderer: metadata.renderer ?? null,
    rendererLabel: metadata.renderer_label ?? null,
    quality: metadata.quality ?? null,
    isFallback: metadata.is_fallback ?? false,
    fallbackReason: metadata.fallback_reason ?? null,
    soundfontId: metadata.soundfont_id ?? null,
    soundfontName: metadata.soundfont_name ?? null,
    soundfontPath: metadata.soundfont_path ?? null,
    warnings: metadata.renderer_warnings ?? [],
  };
}

function audioResultFromAssets(songId: string, assets: AssetsResponse): RenderAudioResponse | null {
  if (!assets.audio) return null;
  return {
    song_id: songId,
    audio_file: "output.wav",
    stream_url: assets.audio.stream_url,
    download_url: assets.audio.download_url,
    metadata: assets.audio.metadata ?? {
      audio_file: "output.wav",
      renderer: "unknown",
      sample_rate: 0,
      duration_seconds: null,
      file_size: 0,
      generated_at: null,
      generator_version: null,
      warnings: [],
    },
  };
}

export function useAudioAssets(songId: string | null | undefined) {
  const [assets, setAssets] = useState<AssetsResponse | null>(null);
  const [midiResult, setMidiResult] = useState<GenerateMidiResponse | null>(null);
  const [audioResult, setAudioResult] = useState<RenderAudioResponse | null>(null);
  const [audioStreamUrl, setAudioStreamUrl] = useState<string | null>(null);
  const [loadingMidi, setLoadingMidi] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // WAV stale：工程配置（SoundFont / MIDI / 版本）变化后，当前 WAV 可能不是最新状态
  const [audioNeedsRender, setAudioNeedsRender] = useState(false);

  const refreshAssets = useCallback(async (): Promise<AssetsResponse | null> => {
    if (!songId) return null;
    setLoadingAssets(true);
    try {
      const result = await getAssets(songId);
      setAssets(result);
      setAudioNeedsRender(Boolean(result.audio_needs_render));
      return result;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingAssets(false);
    }
  }, [songId]);

  const updateFromAssets = useCallback(
    (assetsData: AssetsResponse) => {
      const next = audioResultFromAssets(songId ?? "", assetsData);
      setAudioResult(next);
      if (next) {
        setAudioStreamUrl(`${resolveUrl(next.stream_url)}?t=${Date.now()}`);
      } else {
        setAudioStreamUrl(null);
      }
      setAssets(assetsData);
      setAudioNeedsRender(Boolean(assetsData.audio_needs_render));
    },
    [songId],
  );

  const generateMidi = useCallback(async (): Promise<GenerateMidiResponse | null> => {
    if (!songId) return null;
    setLoadingMidi(true);
    setError(null);
    setAudioResult(null);
    setAudioStreamUrl(null);
    try {
      const result = await generateMidiApi(songId);
      setMidiResult(result);
      await refreshAssets();
      return result;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingMidi(false);
    }
  }, [songId, refreshAssets]);

  const renderAudio = useCallback(async (): Promise<RenderAudioResponse | null> => {
    if (!songId) return null;
    setLoadingAudio(true);
    setError(null);
    try {
      const result = await renderAudioApi(songId);
      setAudioResult(result);
      setAudioStreamUrl(`${resolveUrl(result.stream_url)}?t=${Date.now()}`);
      await refreshAssets();
      setAudioNeedsRender(false);
      return result;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingAudio(false);
    }
  }, [songId, refreshAssets]);

  const resetAssets = useCallback(() => {
    setAssets(null);
    setMidiResult(null);
    setAudioResult(null);
    setAudioStreamUrl(null);
    setAudioNeedsRender(false);
  }, []);

  const markAudioStale = useCallback(() => {
    setAudioNeedsRender(true);
  }, []);

  const clearAudioStale = useCallback(() => {
    setAudioNeedsRender(false);
  }, []);

  const audioRenderMetadata = toAudioRenderMetadata(
    audioResult?.metadata ?? assets?.audio?.metadata ?? null,
  );

  return {
    assets,
    midiResult,
    audioResult,
    audioRenderMetadata,
    audioNeedsRender,
    audioStreamUrl,
    midiDownloadUrl: midiResult ? resolveUrl(midiResult.download_url) : null,
    audioDownloadUrl: audioResult ? resolveUrl(audioResult.download_url) : null,
    stemsDownloadUrl: songId ? resolveUrl(getStemsZipUrl(songId)) : null,
    midiUrl: songId ? resolveUrl(getMidiDownloadUrl(songId)) : null,
    audioStreamPath: songId ? resolveUrl(`/api/v1/songs/${songId}/audio/stream`) : null,
    audioDownloadPath: songId ? resolveUrl(getAudioDownloadUrl(songId)) : null,
    loadingAssets,
    loadingMidi,
    loadingAudio,
    error,
    setError,
    refreshAssets,
    updateFromAssets,
    markAudioStale,
    clearAudioStale,
    generateMidi,
    renderAudio,
    resetAssets,
  };
}

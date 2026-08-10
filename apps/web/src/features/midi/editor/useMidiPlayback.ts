// T34.7 Editor Preview transport：后端 scratch WAV + HTMLAudioElement + RAF playhead。
// Preview 只消费 Editor Session snapshot；不调用 Save/Version/Render WAV API。

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { resolveUrl } from "../../../api/client";
import { getErrorMessage } from "../../../hooks/error";
import {
  createMidiEditorPreview,
  deleteMidiEditorPreview,
  type MidiPreviewScope,
} from "./midiEditorApi";
import {
  buildMidiPreviewTracks,
  clampPlaybackTick,
  isValidLoop,
  previewEndTick,
  secondsToTick,
  tickToSeconds,
} from "./midiPlayback";
import { ticksPerBar } from "./midiEditorLayout";
import type { MidiEditorDocument, MidiEditorNote } from "./midiEditorTypes";

export interface UseMidiPlaybackOptions {
  songId?: string | null;
  document: MidiEditorDocument | null;
  draftNotesByTrack: Record<string, MidiEditorNote[]>;
  selectedTrackId: string | null;
  audioFactory?: () => HTMLAudioElement;
}

export interface UseMidiPlaybackResult {
  scope: MidiPreviewScope;
  setScope: (scope: MidiPreviewScope) => void;
  currentTick: number;
  isPlaying: boolean;
  isPreparing: boolean;
  error: string | null;
  warnings: string[];
  loopEnabled: boolean;
  loopStartTick: number;
  loopEndTick: number;
  loopValid: boolean;
  maxTick: number;
  play: () => Promise<void>;
  stop: () => void;
  seek: (tick: number) => void;
  setLoopEnabled: (enabled: boolean) => boolean;
  setLoopStartTick: (tick: number) => void;
  setLoopEndTick: (tick: number) => void;
}

const defaultAudioFactory = () => new Audio();

/** HTMLAudioElement 级 all-notes-off：立即暂停、断开资源并清空解码缓冲。 */
export function allNotesOff(audio: HTMLAudioElement | null): void {
  if (!audio) return;
  audio.pause();
  audio.removeAttribute("src");
  audio.load();
}

export function useMidiPlayback({
  songId,
  document,
  draftNotesByTrack,
  selectedTrackId,
  audioFactory = defaultAudioFactory,
}: UseMidiPlaybackOptions): UseMidiPlaybackResult {
  const [scope, setScopeState] = useState<MidiPreviewScope>("current_track");
  const [currentTick, setCurrentTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loopEnabled, setLoopEnabledState] = useState(false);
  const [loopStartTick, setLoopStartTickState] = useState(0);
  const [loopEndTick, setLoopEndTickState] = useState(1);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const cleanupUrlRef = useRef<string | null>(null);
  const rafRef = useRef<number | null>(null);
  const generationRef = useRef(0);
  const preparingRef = useRef(false);
  const activeEndTickRef = useRef(0);
  const currentTickRef = useRef(0);
  const loopEnabledRef = useRef(false);
  const loopStartRef = useRef(0);
  const loopEndRef = useRef(1);

  const meter = useMemo(
    () => ({
      numerator: document?.timeSignature[0] ?? 4,
      denominator: document?.timeSignature[1] ?? 4,
    }),
    [document?.timeSignature],
  );
  const allTracks = useMemo(
    () =>
      document
        ? buildMidiPreviewTracks(document, draftNotesByTrack, selectedTrackId, "all_tracks")
        : [],
    [document, draftNotesByTrack, selectedTrackId],
  );
  const maxTick = useMemo(() => {
    if (!document) return 0;
    const contentEnd = previewEndTick(allTracks);
    const projectEnd = Math.ceil(document.totalBars * ticksPerBar(document.ppq, meter));
    return Math.max(contentEnd, projectEnd);
  }, [allTracks, document, meter]);
  const loopValid = isValidLoop(loopStartTick, loopEndTick, maxTick || undefined);

  currentTickRef.current = currentTick;
  loopEnabledRef.current = loopEnabled;
  loopStartRef.current = loopStartTick;
  loopEndRef.current = loopEndTick;

  const releasePreview = useCallback(() => {
    const cleanupUrl = cleanupUrlRef.current;
    cleanupUrlRef.current = null;
    if (cleanupUrl) {
      void deleteMidiEditorPreview(cleanupUrl).catch(() => undefined);
    }
  }, []);

  const halt = useCallback(
    (updateState: boolean) => {
      generationRef.current += 1;
      // 不 abort 已到达后端的 render：否则客户端拿不到 cleanup token。
      // generation guard 会在迟到响应返回后立即 DELETE scratch resource。
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      allNotesOff(audioRef.current);
      audioRef.current = null;
      releasePreview();
      preparingRef.current = false;
      if (updateState) {
        setIsPlaying(false);
        setIsPreparing(false);
      }
    },
    [releasePreview],
  );

  const stop = useCallback(() => halt(true), [halt]);

  const finishPlayback = useCallback(
    (tick: number) => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      allNotesOff(audioRef.current);
      audioRef.current = null;
      releasePreview();
      const clamped = clampPlaybackTick(tick, activeEndTickRef.current);
      currentTickRef.current = clamped;
      setCurrentTick(clamped);
      setIsPlaying(false);
      setIsPreparing(false);
    },
    [releasePreview],
  );

  const startPlayheadRaf = useCallback(
    (audio: HTMLAudioElement, ppq: number, bpm: number) => {
      const update = () => {
        if (audioRef.current !== audio) return;
        let tick = secondsToTick(audio.currentTime, ppq, bpm);
        if (loopEnabledRef.current && tick >= loopEndRef.current) {
          tick = loopStartRef.current;
          audio.currentTime = tickToSeconds(tick, ppq, bpm);
        } else if (!loopEnabledRef.current && tick >= activeEndTickRef.current) {
          finishPlayback(activeEndTickRef.current);
          return;
        }
        currentTickRef.current = tick;
        setCurrentTick(tick);
        rafRef.current = requestAnimationFrame(update);
      };
      rafRef.current = requestAnimationFrame(update);
    },
    [finishPlayback],
  );

  const play = useCallback(async () => {
    if (preparingRef.current || isPlaying) return;
    if (!songId || !document || !selectedTrackId) return;
    if (document.bpm == null || document.bpm <= 0) {
      setError("MIDI tempo 不可用，无法建立 tick 播放时序。");
      return;
    }

    const tracks = buildMidiPreviewTracks(document, draftNotesByTrack, selectedTrackId, scope);
    if (!tracks.length || tracks.every((track) => track.notes.length === 0)) {
      setError("当前 Preview 范围没有可播放的音符。");
      return;
    }
    const endTick = Math.max(previewEndTick(tracks), maxTick);
    if (loopEnabled && !isValidLoop(loopStartTick, loopEndTick, endTick)) {
      setError("Loop 区域无效：Start 必须不小于 0，End 必须大于 Start 且位于工程范围内。");
      return;
    }

    halt(true);
    const generation = generationRef.current;
    preparingRef.current = true;
    setIsPreparing(true);
    setError(null);
    setWarnings([]);
    activeEndTickRef.current = endTick;

    try {
      const result = await createMidiEditorPreview(songId, { scope, tracks });
      if (generation !== generationRef.current) {
        void deleteMidiEditorPreview(result.cleanupUrl).catch(() => undefined);
        return;
      }
      cleanupUrlRef.current = result.cleanupUrl;
      setWarnings(result.warnings);

      const audio = audioFactory();
      audio.preload = "auto";
      audio.src = `${resolveUrl(result.streamUrl)}?t=${Date.now()}`;
      let startTick = clampPlaybackTick(currentTickRef.current, endTick);
      if (startTick >= endTick) startTick = loopEnabled ? loopStartTick : 0;
      if (loopEnabled && (startTick < loopStartTick || startTick >= loopEndTick)) {
        startTick = loopStartTick;
      }
      audio.currentTime = tickToSeconds(startTick, document.ppq, document.bpm);
      audioRef.current = audio;
      audio.addEventListener(
        "ended",
        () => {
          if (loopEnabledRef.current && isValidLoop(loopStartRef.current, loopEndRef.current)) {
            audio.currentTime = tickToSeconds(loopStartRef.current, document.ppq, document.bpm!);
            void audio.play();
            return;
          }
          finishPlayback(activeEndTickRef.current);
        },
        { once: false },
      );
      audio.addEventListener(
        "error",
        () => {
          if (audioRef.current !== audio) return;
          setError("Editor Preview 音频流播放失败，请重试。");
          finishPlayback(currentTickRef.current);
        },
        { once: true },
      );
      await audio.play();
      if (generation !== generationRef.current) {
        allNotesOff(audio);
        return;
      }
      preparingRef.current = false;
      setIsPreparing(false);
      setIsPlaying(true);
      currentTickRef.current = startTick;
      setCurrentTick(startTick);
      startPlayheadRaf(audio, document.ppq, document.bpm);
    } catch (cause) {
      if (generation === generationRef.current) {
        halt(true);
        const code = (cause as { code?: string }).code;
        if (code !== "ABORTED") setError(getErrorMessage(cause));
      }
    }
  }, [
    audioFactory,
    document,
    draftNotesByTrack,
    finishPlayback,
    halt,
    isPlaying,
    loopEnabled,
    loopEndTick,
    loopStartTick,
    maxTick,
    scope,
    selectedTrackId,
    songId,
    startPlayheadRaf,
  ]);

  const seek = useCallback(
    (tick: number) => {
      const next = clampPlaybackTick(tick, maxTick);
      currentTickRef.current = next;
      setCurrentTick(next);
      if (audioRef.current && document?.bpm && document.bpm > 0) {
        audioRef.current.currentTime = tickToSeconds(next, document.ppq, document.bpm);
      }
    },
    [document, maxTick],
  );

  const setLoopEnabled = useCallback(
    (enabled: boolean): boolean => {
      if (enabled && !isValidLoop(loopStartTick, loopEndTick, maxTick || undefined)) {
        setLoopEnabledState(false);
        setError("Loop 区域无效：End 必须大于 Start 且位于工程范围内。");
        return false;
      }
      setError(null);
      setLoopEnabledState(enabled);
      loopEnabledRef.current = enabled;
      return true;
    },
    [loopEndTick, loopStartTick, maxTick],
  );

  const setLoopStartTick = useCallback((tick: number) => {
    setLoopStartTickState(Math.max(0, Math.round(tick)));
  }, []);
  const setLoopEndTick = useCallback((tick: number) => {
    setLoopEndTickState(Math.max(0, Math.round(tick)));
  }, []);
  const setScope = useCallback((nextScope: MidiPreviewScope) => setScopeState(nextScope), []);

  useEffect(() => {
    halt(true);
    setCurrentTick(0);
    currentTickRef.current = 0;
    setLoopEnabledState(false);
    const perBar = document ? ticksPerBar(document.ppq, meter) : 1;
    setLoopStartTickState(0);
    setLoopEndTickState(Math.max(1, Math.min(maxTick || perBar, perBar * 4)));
    return () => halt(false);
  }, [document?.songId, document?.versionId, halt]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    scope,
    setScope,
    currentTick,
    isPlaying,
    isPreparing,
    error,
    warnings,
    loopEnabled,
    loopStartTick,
    loopEndTick,
    loopValid,
    maxTick,
    play,
    stop,
    seek,
    setLoopEnabled,
    setLoopStartTick,
    setLoopEndTick,
  };
}

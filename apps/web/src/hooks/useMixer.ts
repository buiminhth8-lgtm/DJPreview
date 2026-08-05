// useMixer：MixSpec 读取、更新、应用。

import { useCallback, useState } from "react";

import { applyMix as applyMixApi, getMix, updateMix as updateMixApi } from "../api/mixApi";
import type { ApplyMixResponse, MixResponse, MixSpec, TrackMixPatch } from "../api/types";
import { getErrorMessage } from "./error";

export function useMixer(songId?: string | null) {
  const [mixSpec, setMixSpec] = useState<MixSpec | null>(null);
  const [loadingMix, setLoadingMix] = useState(false);
  const [applyingMix, setApplyingMix] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshMix = useCallback(async (): Promise<MixResponse | null> => {
    if (!songId) return null;
    setLoadingMix(true);
    setError(null);
    try {
      const result = await getMix(songId);
      setMixSpec(result.mix_spec);
      return result;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingMix(false);
    }
  }, [songId]);

  const updateMix = useCallback(
    async (patch: { master_volume?: number; tracks: TrackMixPatch[] }, apply = false) => {
      if (!songId) return null;
      setError(null);
      try {
        const result = await updateMixApi(songId, patch, apply);
        setMixSpec(result.mix_spec);
        return result;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      }
    },
    [songId],
  );

  const applyMix = useCallback(async (): Promise<ApplyMixResponse | null> => {
    if (!songId) return null;
    setApplyingMix(true);
    setError(null);
    try {
      const result = await applyMixApi(songId);
      setMixSpec(result.mix_spec);
      return result;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setApplyingMix(false);
    }
  }, [songId]);

  return {
    mixSpec,
    loadingMix,
    applyingMix,
    error,
    setError,
    refreshMix,
    updateMix,
    applyMix,
  };
}

// useSoundfonts：音源列表 / 扫描 / 项目音源选择。

import { useCallback, useState } from "react";

import {
  getProjectSoundfont,
  listSoundfonts,
  scanSoundfonts,
  setProjectSoundfont,
} from "../api/soundfontApi";
import type { ProjectSoundfontResponse, SoundFontInfo, SoundfontListResponse } from "../api/types";
import { getErrorMessage } from "./error";

export function useSoundfonts(songId?: string | null) {
  const [soundfonts, setSoundfonts] = useState<SoundFontInfo[]>([]);
  const [defaultSoundfontId, setDefaultSoundfontId] = useState<string | null>(null);
  const [projectSoundfont, setProjectSoundfontState] = useState<ProjectSoundfontResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyList = useCallback((response: SoundfontListResponse) => {
    setSoundfonts(response.soundfonts);
    setDefaultSoundfontId(response.default_soundfont_id);
  }, []);

  const loadSoundfonts = useCallback(async (): Promise<SoundfontListResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await listSoundfonts();
      applyList(response);
      return response;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, [applyList]);

  const rescan = useCallback(async (): Promise<SoundfontListResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await scanSoundfonts();
      applyList(response);
      return response;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, [applyList]);

  const loadProjectSoundfont = useCallback(
    async (): Promise<ProjectSoundfontResponse | null> => {
      if (!songId) {
        setProjectSoundfontState(null);
        return null;
      }
      try {
        const response = await getProjectSoundfont(songId);
        setProjectSoundfontState(response);
        return response;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      }
    },
    [songId],
  );

  const selectSoundfont = useCallback(
    async (soundfontId: string): Promise<ProjectSoundfontResponse | null> => {
      if (!songId) return null;
      setError(null);
      try {
        const response = await setProjectSoundfont(songId, { soundfont_id: soundfontId });
        setProjectSoundfontState(response);
        return response;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      }
    },
    [songId],
  );

  return {
    soundfonts,
    defaultSoundfontId,
    projectSoundfont,
    loading,
    error,
    setError,
    loadSoundfonts,
    rescan,
    loadProjectSoundfont,
    selectSoundfont,
  };
}

// useSongProject：歌曲 / 项目核心状态（生成、读取、编辑、重置）。

import { useCallback, useState } from "react";

import { editSong, generateMusicSpec, getSong } from "../api/songApi";
import type { EditSongResponse, GenerateSongResponse, MusicSpec } from "../api/types";
import { getErrorMessage } from "./error";

export function useSongProject() {
  const [songId, setSongId] = useState<string | null>(null);
  const [musicSpec, setMusicSpec] = useState<MusicSpec | null>(null);
  const [prompt, setPrompt] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [validation, setValidation] = useState<GenerateSongResponse["validation"]>(null);
  const [loadingSpec, setLoadingSpec] = useState(false);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetProject = useCallback(() => {
    setSongId(null);
    setMusicSpec(null);
    setValidation(null);
    setPrompt("");
    setEditInstruction("");
    setError(null);
  }, []);

  const generate = useCallback(
    async (
      promptText: string,
      styleTemplateId?: string | null,
      styleStrength = 0.7,
    ): Promise<GenerateSongResponse | null> => {
      if (!promptText.trim()) {
        setError("请输入音乐描述");
        return null;
      }
      setLoadingSpec(true);
      setError(null);
      try {
        const result = await generateMusicSpec(promptText.trim(), styleTemplateId || null, styleStrength);
        setSongId(result.song_id);
        setMusicSpec(result.music_spec);
        setValidation(result.validation ?? null);
        return result;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      } finally {
        setLoadingSpec(false);
      }
    },
    [],
  );

  const loadSong = useCallback(async (newSongId: string): Promise<MusicSpec | null> => {
    try {
      const result = await getSong(newSongId);
      setSongId(newSongId);
      setMusicSpec(result.music_spec);
      return result.music_spec;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    }
  }, []);

  const edit = useCallback(
    async (instruction: string): Promise<EditSongResponse | null> => {
      if (!songId) {
        setError("请先生成或加载歌曲");
        return null;
      }
      if (!instruction.trim()) {
        setError("请输入修改指令");
        return null;
      }
      setLoadingEdit(true);
      setError(null);
      try {
        const result = await editSong(songId, instruction.trim());
        setMusicSpec(result.music_spec);
        return result;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      } finally {
        setLoadingEdit(false);
      }
    },
    [songId],
  );

  return {
    songId,
    setSongId,
    musicSpec,
    setMusicSpec,
    prompt,
    setPrompt,
    editInstruction,
    setEditInstruction,
    validation,
    loadingSpec,
    loadingEdit,
    error,
    setError,
    generate,
    loadSong,
    edit,
    resetProject,
  };
}

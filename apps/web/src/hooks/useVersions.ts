// useVersions：版本列表 / 详情 / diff / 恢复。

import { useCallback, useState } from "react";

import { getVersion, getVersionDiff, getVersions, restoreVersion as restoreVersionApi } from "../api/versionApi";
import type {
  RestoreVersionResponse,
  VersionDetailResponse,
  VersionDiffResponse,
  VersionInfo,
} from "../api/types";
import { getErrorMessage } from "./error";

interface UseVersionsParams {
  songId?: string | null;
  onSongRestored?: () => void | Promise<void>;
  onAssetsChanged?: () => void | Promise<void>;
}

export function useVersions(params: UseVersionsParams = {}) {
  const [versions, setVersions] = useState<VersionInfo[] | null>(null);
  const [currentVersionId, setCurrentVersionId] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [versionDetail, setVersionDetail] = useState<VersionDetailResponse | null>(null);
  const [versionDiff, setVersionDiff] = useState<VersionDiffResponse | null>(null);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [restoringVersion, setRestoringVersion] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshVersions = useCallback(async (): Promise<VersionInfo[] | null> => {
    if (!params.songId) return null;
    setLoadingVersions(true);
    setError(null);
    try {
      const result = await getVersions(params.songId);
      setVersions(result.versions);
      setCurrentVersionId(result.current_version_id);
      return result.versions;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingVersions(false);
    }
  }, [params.songId]);

  const loadVersionDetail = useCallback(
    async (versionId: string): Promise<VersionDetailResponse | null> => {
      if (!params.songId) return null;
      try {
        const detail = await getVersion(params.songId, versionId);
        setVersionDetail(detail);
        return detail;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      }
    },
    [params.songId],
  );

  const loadVersionDiff = useCallback(
    async (versionId: string): Promise<VersionDiffResponse | null> => {
      if (!params.songId) return null;
      try {
        const diff = await getVersionDiff(params.songId, versionId);
        setVersionDiff(diff);
        return diff;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      }
    },
    [params.songId],
  );

  const restoreVersion = useCallback(
    async (versionId: string): Promise<RestoreVersionResponse | null> => {
      if (!params.songId) return null;
      setRestoringVersion(true);
      setError(null);
      try {
        const result = await restoreVersionApi(params.songId, versionId);
        setCurrentVersionId(versionId);
        setSelectedVersionId(versionId);
        await params.onSongRestored?.();
        await params.onAssetsChanged?.();
        return result;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      } finally {
        setRestoringVersion(false);
      }
    },
    [params.songId, params.onSongRestored, params.onAssetsChanged],
  );

  const resetVersions = useCallback(() => {
    setVersions(null);
    setCurrentVersionId(null);
    setSelectedVersionId(null);
    setVersionDetail(null);
    setVersionDiff(null);
  }, []);

  return {
    versions,
    currentVersionId,
    selectedVersionId,
    setSelectedVersionId,
    versionDetail,
    versionDiff,
    loadingVersions,
    restoringVersion,
    error,
    setError,
    refreshVersions,
    loadVersionDetail,
    loadVersionDiff,
    restoreVersion,
    resetVersions,
  };
}

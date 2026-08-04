import { useEffect, useState } from "react";
import {
  applyMix,
  getMix,
  updateMix,
  type AssetsResponse,
  type MixSpec,
  type TrackMixSpec,
} from "../api/musicApi";
import TrackMixerStrip from "./TrackMixerStrip";

interface MixerPanelProps {
  songId: string;
  refreshKey?: number;
  onApplied: (assets: AssetsResponse) => void;
  onError: (message: string) => void;
}

export default function MixerPanel({ songId, refreshKey = 0, onApplied, onError }: MixerPanelProps) {
  const [mix, setMix] = useState<MixSpec | null>(null);
  const [busy, setBusy] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);

  // 轨道/版本变化（编辑、恢复、优化）后重新加载 MixSpec
  useEffect(() => {
    setMix(null);
    setWarnings([]);
    getMix(songId)
      .then((res) => setMix(res.mix_spec))
      .catch((e) => onError(e instanceof Error ? e.message : String(e)));
  }, [songId, refreshKey, onError]);

  const handleChange = (trackId: string, patch: Partial<TrackMixSpec>) => {
    setMix((prev) =>
      prev
        ? {
            ...prev,
            tracks: prev.tracks.map((t) => (t.track_id === trackId ? { ...t, ...patch } : t)),
          }
        : prev,
    );
  };

  const buildPatch = () => {
    if (!mix) return { tracks: [] as Array<Partial<TrackMixSpec> & { track_id: string }> };
    return {
      master_volume: mix.master_volume,
      tracks: mix.tracks.map((t) => ({
        track_id: t.track_id,
        volume: t.volume,
        pan: t.pan,
        mute: t.mute,
        solo: t.solo,
        enabled: t.enabled,
        velocity_scale: t.velocity_scale,
      })),
    };
  };

  // apply=false：仅保存；apply=true：保存后调用 /mix/apply 一次性重渲染
  const handleApply = async (apply: boolean) => {
    if (!mix) return;
    setBusy(true);
    setWarnings([]);
    try {
      const saved = await updateMix(songId, buildPatch(), false);
      setMix(saved.mix_spec);
      if (apply) {
        const applied = await applyMix(songId);
        setMix(applied.mix_spec);
        setWarnings(applied.warnings);
        onApplied(applied.assets);
      }
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!mix) {
    return <div className="muted-note">加载 MixSpec…</div>;
  }

  return (
    <div className="mixer-panel">
      <label className="mixer-control master-volume">
        master_volume
        <input
          type="range"
          min={0}
          max={1.5}
          step={0.05}
          value={mix.master_volume}
          onChange={(e) => setMix({ ...mix, master_volume: Number(e.target.value) })}
        />
        <span>{mix.master_volume.toFixed(2)}</span>
      </label>
      <div className="mixer-strips">
        {mix.tracks.map((track) => (
          <TrackMixerStrip key={track.track_id} track={track} onChange={handleChange} />
        ))}
      </div>
      <div className="actions">
        <button onClick={() => handleApply(false)} disabled={busy}>
          {busy ? "处理中…" : "保存混音"}
        </button>
        <button onClick={() => handleApply(true)} disabled={busy}>
          {busy ? "渲染中…" : "应用混音并重新渲染"}
        </button>
      </div>
      {warnings.length > 0 && (
        <div className="warnings">提示：{warnings.join("；")}</div>
      )}
    </div>
  );
}

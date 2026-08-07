import { useEffect, useState } from "react";
import {
  regenerateSong,
  type MusicSpec,
  type RegenerationRequest,
  type RegenerationResult,
} from "../../api/musicApi";

interface RegenerationPanelProps {
  songId: string;
  spec: MusicSpec;
  onRegenerated: (result: RegenerationResult) => void;
  onError: (message: string) => void;
}

export default function RegenerationPanel({
  songId,
  spec,
  onRegenerated,
  onError,
}: RegenerationPanelProps) {
  const [scope, setScope] = useState<RegenerationRequest["scope"]>("section");
  const [sectionId, setSectionId] = useState(spec.form[0]?.id ?? "chorus");
  const [trackId, setTrackId] = useState(spec.tracks[0]?.id ?? "");
  const [instruction, setInstruction] = useState("");
  const [variation, setVariation] = useState(0.5);
  const [keepHarmony, setKeepHarmony] = useState(true);
  const [keepMelody, setKeepMelody] = useState(false);
  const [keepRhythm, setKeepRhythm] = useState(false);
  const [autoRender, setAutoRender] = useState(true);
  const [busy, setBusy] = useState(false);

  // 版本/曲式变化后同步段落与轨道选项
  useEffect(() => {
    if (spec.form.length > 0 && !spec.form.some((s) => s.id === sectionId)) {
      setSectionId(spec.form[0].id);
    }
    if (spec.tracks.length > 0 && !spec.tracks.some((t) => t.id === trackId)) {
      setTrackId(spec.tracks[0].id);
    }
  }, [spec, sectionId, trackId]);

  const handleRegenerate = async () => {
    setBusy(true);
    try {
      const request: RegenerationRequest = {
        scope,
        section_id: scope === "section" || scope === "section_track" ? sectionId : null,
        track_id: scope === "track" || scope === "section_track" ? trackId : null,
        instruction: instruction.trim() || null,
        keep_harmony: keepHarmony,
        keep_melody: keepMelody,
        keep_rhythm: keepRhythm,
        variation_strength: variation,
        seed_offset: 1,
        auto_render: autoRender,
      };
      const result = await regenerateSong(songId, request);
      onRegenerated(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="regeneration-panel">
      <div className="actions">
        <select value={scope} onChange={(e) => setScope(e.target.value as RegenerationRequest["scope"])}>
          <option value="section">段落</option>
          <option value="track">轨道</option>
          <option value="section_track">段落 + 轨道</option>
          <option value="overall">整体</option>
        </select>
        {(scope === "section" || scope === "section_track") && (
          <select value={sectionId} onChange={(e) => setSectionId(e.target.value)}>
            {spec.form.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}（{s.id}）
              </option>
            ))}
          </select>
        )}
        {(scope === "track" || scope === "section_track") && (
          <select value={trackId} onChange={(e) => setTrackId(e.target.value)}>
            {spec.tracks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.id}（{t.role}）
              </option>
            ))}
          </select>
        )}
      </div>
      <textarea
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        placeholder="例如：让副歌旋律变化更明显（可选）"
        rows={2}
      />
      <label className="mixer-control" style={{ gridTemplateColumns: "160px 1fr 42px" }}>
        variation_strength
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={variation}
          onChange={(e) => setVariation(Number(e.target.value))}
        />
        <span>{variation.toFixed(2)}</span>
      </label>
      <div className="mixer-checks">
        <label>
          <input type="checkbox" checked={keepHarmony} onChange={(e) => setKeepHarmony(e.target.checked)} />
          keep_harmony
        </label>
        <label>
          <input type="checkbox" checked={keepMelody} onChange={(e) => setKeepMelody(e.target.checked)} />
          keep_melody
        </label>
        <label>
          <input type="checkbox" checked={keepRhythm} onChange={(e) => setKeepRhythm(e.target.checked)} />
          keep_rhythm
        </label>
        <label>
          <input type="checkbox" checked={autoRender} onChange={(e) => setAutoRender(e.target.checked)} />
          auto_render
        </label>
      </div>
      <div className="actions">
        <button onClick={handleRegenerate} disabled={busy}>
          {busy ? "重生成中…" : "局部重生成"}
        </button>
      </div>
    </div>
  );
}

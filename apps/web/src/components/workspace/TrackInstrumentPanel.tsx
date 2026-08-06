// TrackInstrumentPanel：轨道与乐器（常驻）。
// 无 tracks 时 Empty State；有数据时显示轨道表 + 轨道/乐器 warning + instrument normalization 信息。

import type { MusicSpec } from "../../api/types";
import { EmptyState, InlineNotice, SectionCard } from "../ui";

export interface TrackInstrumentPanelProps {
  musicSpec?: MusicSpec | null;
  warnings?: unknown[] | null;
  debug?: unknown;
}

interface TrackLike {
  id?: string;
  role?: string;
  instrument?: string;
  pattern?: string | null;
  register?: string | null;
  velocity?: number;
  enabled_sections?: string[] | null;
}

const DASH = "—";

function toTracks(musicSpec: MusicSpec | undefined | null): TrackLike[] {
  if (!musicSpec) return [];
  return (musicSpec.tracks ?? []).map((t) => ({
    id: t.id,
    role: t.role,
    instrument: t.instrument,
    pattern: t.pattern,
    register: t.register,
    velocity: t.velocity,
    enabled_sections: t.enabled_sections,
  }));
}

function trackWarnings(warnings: unknown[]): { trackId: string; message: string }[] {
  const result: { trackId: string; message: string }[] = [];
  for (const w of warnings ?? []) {
    if (typeof w === "string") continue;
    if (typeof w !== "object" || w === null) continue;
    const rec = w as Record<string, unknown>;
    const trackId = rec.track_id ?? rec.trackId ?? rec.track;
    if (typeof trackId === "string") {
      const message =
        typeof rec.message === "string" ? rec.message : typeof w === "object" ? JSON.stringify(rec) : String(w);
      result.push({ trackId, message });
    }
  }
  return result;
}

function normalizationNotes(warnings: unknown[]): string[] {
  const notes: string[] = [];
  for (const w of warnings ?? []) {
    if (typeof w === "string") continue;
    if (typeof w !== "object" || w === null) continue;
    const rec = w as Record<string, unknown>;
    // UNKNOWN_INSTRUMENT_ALIAS 里可能带建议；normalize 成功则不会出现 warning。
    const message = typeof rec.message === "string" ? rec.message : "";
    const m = message.match(/建议使用 '([^']+)'/);
    if (m) notes.push(`建议归一化：${rec.instrument ?? ""} → ${m[1]}`);
  }
  return notes;
}

export function TrackInstrumentPanel({ musicSpec, warnings }: TrackInstrumentPanelProps) {
  const tracks = toTracks(musicSpec);
  const tw = trackWarnings(warnings ?? []);
  const normNotes = normalizationNotes(warnings ?? []);

  if (tracks.length === 0) {
    return (
      <SectionCard title="轨道与乐器" description="编曲轨道列表">
        <EmptyState
          title="暂无轨道"
          description="生成 MusicSpec 后将在这里显示 melody、harmony、bass、drums 等编曲轨道。"
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title="轨道与乐器"
      description="编曲轨道列表"
      badge={tw.length > 0 ? <span className="status-chip status-error">{tw.length} warnings</span> : undefined}
    >
      {normNotes.length > 0 && (
        <div className="workspace-track-normalization">
          {normNotes.map((n, i) => (
            <InlineNotice key={i} variant="info">
              {n}
            </InlineNotice>
          ))}
        </div>
      )}

      <div className="workspace-track-table-wrap">
        <table className="workspace-track-table">
          <thead>
            <tr>
              <th>Track ID</th>
              <th>Role</th>
              <th>Instrument</th>
              <th>Pattern</th>
              <th>Register</th>
              <th>Velocity</th>
              <th>Enabled Sections</th>
            </tr>
          </thead>
          <tbody>
            {tracks.map((t, i) => (
              <tr key={t.id ?? `track-${i}`}>
                <td>{t.id ?? DASH}</td>
                <td>{t.role ?? DASH}</td>
                <td>{t.instrument ?? DASH}</td>
                <td>{t.pattern ?? DASH}</td>
                <td>{t.register ?? DASH}</td>
                <td>{typeof t.velocity === "number" ? t.velocity : DASH}</td>
                <td>{t.enabled_sections && t.enabled_sections.length > 0 ? t.enabled_sections.join(", ") : "全部"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {tw.length > 0 && (
        <div className="workspace-track-warnings">
          {tw.map((item, i) => (
            <InlineNotice key={i} variant="warning" title={`轨道 ${item.trackId}`}>
              {item.message}
            </InlineNotice>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

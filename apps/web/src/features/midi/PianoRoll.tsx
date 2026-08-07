import { useEffect, useMemo, useState } from "react";
import { getPianoRoll, type PianoRollData } from "../../api/musicApi";

interface PianoRollProps {
  songId: string;
  refreshKey: number;
  onError: (message: string) => void;
}

const TRACK_COLORS = ["#6c8cff", "#4ecb8d", "#e0b45a", "#c06cff", "#ff7b72", "#56c8d8"];

export default function PianoRoll({ songId, refreshKey, onError }: PianoRollProps) {
  const [data, setData] = useState<PianoRollData | null>(null);
  const [loading, setLoading] = useState(true);
  const [trackFilter, setTrackFilter] = useState<string>("");

  useEffect(() => {
    setLoading(true);
    getPianoRoll(songId)
      .then(setData)
      .catch((e) => onError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [songId, refreshKey, onError]);

  const tracks = useMemo(() => {
    if (!data) return [];
    return trackFilter ? data.tracks.filter((t) => t.role === trackFilter || t.track_name === trackFilter) : data.tracks;
  }, [data, trackFilter]);

  if (loading) return <div className="muted-note">加载钢琴卷帘…</div>;
  if (!data) return <div className="muted-note">暂无 Piano Roll 数据。</div>;

  const ppb = 24; // px per beat
  const ppp = 6; // px per pitch
  const minPitch = Math.min(...data.tracks.map((t) => t.min_pitch ?? 60), 60);
  const maxPitch = Math.max(...data.tracks.map((t) => t.max_pitch ?? 72), 72);
  const width = Math.max(480, data.total_bars * data.beats_per_bar * ppb);
  const height = (maxPitch - minPitch + 2) * ppp;
  const roleOptions = Array.from(new Set(data.tracks.map((t) => t.role ?? t.track_name ?? "?")));

  return (
    <div className="piano-roll">
      <div className="piano-roll-toolbar">
        <select value={trackFilter} onChange={(e) => setTrackFilter(e.target.value)}>
          <option value="">全部轨道</option>
          {roleOptions.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
        <span className="muted-note">
          {data.total_notes} 个音符 {data.truncated ? "（已截断）" : ""} · {data.bpm ?? "?"} BPM
        </span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="piano-roll-svg"
        style={{ maxWidth: "100%" }}
      >
        {/* 段落背景 */}
        {data.sections.map((section) => {
          const x = (section.start_bar - 1) * data.beats_per_bar * ppb;
          const w = section.bars * data.beats_per_bar * ppb;
          return (
            <rect
              key={section.id}
              x={x}
              y={0}
              width={w}
              height={height}
              fill={section.energy > 0.7 ? "rgba(108,140,255,0.10)" : "rgba(255,255,255,0.03)"}
            />
          );
        })}
        {/* 小节线 */}
        {Array.from({ length: Math.ceil(data.total_bars) + 1 }, (_, i) => (
          <line
            key={`bar-${i}`}
            x1={i * data.beats_per_bar * ppb}
            y1={0}
            x2={i * data.beats_per_bar * ppb}
            y2={height}
            stroke="rgba(255,255,255,0.12)"
            strokeWidth={1}
          />
        ))}
        {/* 音符 */}
        {tracks.map((track, ti) => (
          <g key={track.track_index}>
            {track.notes.map((note, ni) => (
              <rect
                key={`${track.track_index}-${ni}`}
                x={note.start_beat * ppb}
                y={(maxPitch - note.pitch) * ppp}
                width={Math.max(3, note.duration_beats * ppb - 1)}
                height={ppp - 1}
                rx={1}
                fill={TRACK_COLORS[ti % TRACK_COLORS.length]}
                opacity={note.is_drum ? 0.55 : 0.9}
              >
                <title>{`${note.pitch_name} @${note.start_beat} (${note.duration_beats} beats)`}</title>
              </rect>
            ))}
          </g>
        ))}
      </svg>
      {data.truncated && <div className="muted-note">音符过多，仅展示前 5000 个。</div>}
    </div>
  );
}

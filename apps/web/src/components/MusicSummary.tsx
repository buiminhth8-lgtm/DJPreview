import type { MusicSpec } from "../api/musicApi";

interface MusicSummaryProps {
  spec: MusicSpec;
}

export default function MusicSummary({ spec }: MusicSummaryProps) {
  const rows: Array<[string, string]> = [
    ["标题", spec.title],
    ["BPM", `${spec.tempo.bpm}${spec.tempo.feel ? `（${spec.tempo.feel}）` : ""}`],
    ["拍号", `${spec.meter.numerator}/${spec.meter.denominator}`],
    [
      "调性",
      `${spec.tonality.key} ${spec.tonality.mode}${spec.tonality.scale ? ` · ${spec.tonality.scale}` : ""}`,
    ],
    ["总小节数", `${spec.length.bars} bars`],
    ["风格", spec.style.join(", ") || "—"],
    ["情绪", spec.mood.join(", ") || "—"],
    ["生成 seed", String(spec.seed)],
  ];

  return (
    <div className="summary">
      {rows.map(([label, value]) => (
        <div className="summary-row" key={label}>
          <span className="summary-label">{label}</span>
          <span className="summary-value">{value}</span>
        </div>
      ))}
    </div>
  );
}

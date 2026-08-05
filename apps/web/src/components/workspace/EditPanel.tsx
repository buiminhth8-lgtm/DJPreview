// 自然语言修改面板。

import type { DiffItem } from "../../api/types";

export interface EditPanelProps {
  value: string;
  loading: boolean;
  diff: DiffItem[] | null;
  onChange: (value: string) => void;
  onApply: () => void;
}

function formatDiff(diff: DiffItem[]): string {
  return diff
    .map((d) => {
      const oldV = typeof d.old === "object" ? JSON.stringify(d.old) : String(d.old ?? "—");
      const newV = typeof d.new === "object" ? JSON.stringify(d.new) : String(d.new ?? "—");
      return `${d.field}: ${oldV} → ${newV}`;
    })
    .join("\n");
}

export default function EditPanel({ value, loading, diff, onChange, onApply }: EditPanelProps) {
  return (
    <section className="panel result">
      <h2>自然语言修改</h2>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="例如：副歌更亮一点 / 整首更快一点 / 加点中国风 / 去掉贝斯 / 副歌加鼓"
        rows={3}
        disabled={loading}
      />
      <div className="actions">
        <button onClick={onApply} disabled={loading}>
          {loading ? "修改中…" : "应用修改"}
        </button>
      </div>
      {diff && diff.length > 0 && (
        <div className="diff-box">
          <h3>修改内容</h3>
          <pre>{formatDiff(diff)}</pre>
        </div>
      )}
      {diff && diff.length === 0 && <p className="muted-note">本次修改未产生字段变化。</p>}
    </section>
  );
}

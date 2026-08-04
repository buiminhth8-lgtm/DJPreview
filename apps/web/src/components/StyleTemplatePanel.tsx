import { useEffect, useState } from "react";
import { listStyles, type StyleTemplateSpec } from "../api/musicApi";

interface StyleTemplatePanelProps {
  value: string;
  strength: number;
  onChange: (styleId: string, strength: number) => void;
  onError: (message: string) => void;
}

export default function StyleTemplatePanel({ value, strength, onChange, onError }: StyleTemplatePanelProps) {
  const [styles, setStyles] = useState<StyleTemplateSpec[]>([]);
  const [selected, setSelected] = useState<StyleTemplateSpec | null>(null);

  useEffect(() => {
    listStyles()
      .then((list) => {
        setStyles(list);
        const found = list.find((s) => s.id === value) ?? null;
        setSelected(found);
      })
      .catch((e) => onError(e instanceof Error ? e.message : String(e)));
  }, [value, onError]);

  const handleSelect = (id: string) => {
    const found = styles.find((s) => s.id === id) ?? null;
    setSelected(found);
    onChange(id, strength);
  };

  return (
    <div className="style-panel">
      <div className="actions">
        <select value={value} onChange={(e) => handleSelect(e.target.value)}>
          <option value="">不使用风格模板</option>
          {styles.map((style) => (
            <option key={style.id} value={style.id}>
              {style.name}（{style.id}）
            </option>
          ))}
        </select>
        <label className="mixer-control" style={{ gridTemplateColumns: "120px 1fr 42px" }}>
          风格强度
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={strength}
            onChange={(e) => onChange(value, Number(e.target.value))}
          />
          <span>{strength.toFixed(2)}</span>
        </label>
      </div>
      {selected && (
        <div className="style-detail">
          <p>
            <strong>{selected.name}</strong>：{selected.description}
          </p>
          <p>
            标签：{selected.tags.join(" / ")} · 默认 BPM：{selected.default_tempo ?? "—"} ·
            推荐轨道：{selected.default_tracks.map((t) => String(t.role ?? t.id)).join(" / ")}
          </p>
        </div>
      )}
    </div>
  );
}

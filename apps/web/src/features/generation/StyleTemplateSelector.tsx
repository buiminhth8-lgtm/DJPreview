// features/generation/StyleTemplateSelector.tsx（T33.4）
// 风格模板选择：模板列表 + 强度滑杆。失败不阻塞基础生成。

import type { StyleTemplateSpec } from "../../api/types";

export interface StyleTemplateSelectorProps {
  styles: StyleTemplateSpec[];
  selectedId: string;
  strength: number;
  loadError?: string | null;
  onSelect: (id: string) => void;
  onStrengthChange: (value: number) => void;
}

export function StyleTemplateSelector({
  styles,
  selectedId,
  strength,
  loadError,
  onSelect,
  onStrengthChange,
}: StyleTemplateSelectorProps) {
  const selected = styles.find((s) => s.id === selectedId) ?? null;
  const hasTemplate = Boolean(selectedId);

  return (
    <div className="generate-panel__style">
      <label className="generate-panel__label" htmlFor="style-template-select">
        风格模板
      </label>
      <select
        id="style-template-select"
        value={selectedId}
        onChange={(e) => onSelect(e.target.value)}
      >
        <option value="">不使用风格模板</option>
        {styles.map((style) => (
          <option key={style.id} value={style.id}>
            {style.name}（{style.id}）
          </option>
        ))}
      </select>

      {selected && <p className="generate-panel__style-detail">{selected.description}</p>}
      {loadError && (
        <p className="generate-panel__style-warning" role="note">
          风格模板加载失败，可继续使用基础生成。
        </p>
      )}

      <label className="generate-panel__strength" htmlFor="style-strength-slider">
        风格强度：{strength.toFixed(2)}
      </label>
      <input
        id="style-strength-slider"
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={strength}
        disabled={!hasTemplate}
        aria-label="风格强度"
        onChange={(e) => onStrengthChange(Number(e.target.value))}
      />
    </div>
  );
}

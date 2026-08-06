// EditSongPanel：自然语言修改（常驻，T38-G）。
// 无工程时 Empty State + 输入区 disabled；有工程时输入指令 + 应用修改（+ 应用并重新渲染）。

import { useState } from "react";
import type { DiffItem } from "../../api/types";
import { ActionButton, ButtonRow, EmptyState, SectionCard } from "../ui";

export interface EditSongPanelProps {
  songId?: string | null;
  hasProject?: boolean;
  isEditing?: boolean;
  editError?: unknown;
  initialInstruction?: string;
  diff?: DiffItem[] | null;
  onEditSong?: (instruction: string, options?: { autoRender?: boolean }) => void;
}

export function EditSongPanel({
  songId,
  hasProject = false,
  isEditing = false,
  editError,
  initialInstruction = "",
  diff,
  onEditSong,
}: EditSongPanelProps) {
  const [instruction, setInstruction] = useState(initialInstruction);
  const [showAutoRender, setShowAutoRender] = useState(true);

  const hasSong = Boolean(songId) && hasProject;
  const emptyInstruction = instruction.trim().length === 0;

  const apply = (autoRender: boolean) => {
    if (!hasSong || emptyInstruction || isEditing) return;
    onEditSong?.(instruction.trim(), { autoRender });
  };

  let body;
  if (!hasSong) {
    body = (
      <EmptyState
        title="请先生成或导入工程"
        description="创建工程后，可输入“让副歌更宏大”“把鼓组改得更重”等指令修改音乐。"
      />
    );
  } else {
    body = (
      <div className="workspace-edit-song">
        <textarea
          className="generate-console__textarea workspace-edit-song__textarea"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="例如：让副歌更宏大，加入更强的 brass 和 crash，鼓组更紧张。"
          rows={3}
          disabled={isEditing}
        />
        <ButtonRow className="workspace-edit-actions">
          <ActionButton
            variant="primary"
            onClick={() => apply(false)}
            disabled={!hasSong || emptyInstruction || isEditing}
            disabledReason={!hasSong ? "请先生成或导入工程" : emptyInstruction ? "请输入修改指令" : undefined}
            loading={isEditing}
          >
            {isEditing ? "正在应用修改…" : "应用修改"}
          </ActionButton>
          {showAutoRender && (
            <ActionButton
              variant="secondary"
              onClick={() => apply(true)}
              disabled={!hasSong || emptyInstruction || isEditing}
              disabledReason={!hasSong ? "请先生成工程并输入修改指令" : emptyInstruction ? "请输入修改指令" : undefined}
            >
              应用并重新渲染
            </ActionButton>
          )}
        </ButtonRow>
        <label className="workspace-edit-song__auto-render">
          <input type="checkbox" checked={showAutoRender} onChange={(e) => setShowAutoRender(e.target.checked)} />
          默认自动重新渲染 WAV
        </label>
        {editError != null && (
          <div className="ui-inline-notice ui-inline-notice--danger">✕ {String(editError)}</div>
        )}
        {diff && diff.length > 0 && (
          <div className="workspace-edit-song__diff">
            <h3>修改内容</h3>
            <pre>{formatDiff(diff)}</pre>
          </div>
        )}
        {diff && diff.length === 0 && <p className="muted-note">本次修改未产生字段变化。</p>}
      </div>
    );
  }

  return (
    <SectionCard title="自然语言修改" description="用一句话修改音乐">
      {body}
    </SectionCard>
  );
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

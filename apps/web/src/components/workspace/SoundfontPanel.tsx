// SoundfontPanel：音源管理（常驻，T38-H）。
// 无工程时扫描可用；「应用到当前工程」disabled 并显示原因；有工程才请求项目音源。

import { useEffect } from "react";
import { useSoundfonts } from "../../hooks";
import type { SoundFontInfo } from "../../api/types";
import { ActionButton, ButtonRow, EmptyState, SectionCard, StatusBadge } from "../ui";

export interface SoundfontPanelProps {
  songId?: string | null;
  onError?: (message: string) => void;
}

export function SoundfontPanel({ songId, onError }: SoundfontPanelProps) {
  const sf = useSoundfonts(songId);

  useEffect(() => {
    void sf.loadSoundfonts();
  }, [sf.loadSoundfonts]);

  useEffect(() => {
    void sf.loadProjectSoundfont();
  }, [sf.loadProjectSoundfont]);

  useEffect(() => {
    if (sf.error) onError?.(sf.error);
  }, [sf.error, onError]);

  const hasSong = Boolean(songId);
  const selectedId = sf.projectSoundfont?.soundfont?.soundfont_id ?? null;
  const list = Array.isArray(sf.soundfonts) ? sf.soundfonts : ([] as SoundFontInfo[]);

  let body;
  if (list.length === 0) {
    body = (
      <EmptyState
        title="暂无已扫描音源"
        description="可以扫描本地 SoundFont 目录。仓库不会包含真实 .sf2 / .sf3 / .sfz 文件。"
        action={
          <ButtonRow>
            <ActionButton variant="secondary" onClick={() => void sf.rescan()} disabled={sf.loading} loading={sf.loading}>
              {sf.loading ? "扫描中…" : "扫描音源"}
            </ActionButton>
          </ButtonRow>
        }
      />
    );
  } else {
    body = (
      <div className="workspace-soundfont">
        <ButtonRow className="workspace-soundfont__actions">
          <ActionButton variant="secondary" onClick={() => void sf.rescan()} disabled={sf.loading} loading={sf.loading}>
            {sf.loading ? "扫描中…" : "重新扫描"}
          </ActionButton>
        </ButtonRow>
        {!hasSong && (
          <p className="workspace-soundfont__hint">
            暂无当前工程：可以先扫描音源；生成或导入工程后可将音源应用到当前工程。
          </p>
        )}
        <div className="workspace-soundfont-list">
          {list.map((item) => {
            const isSelected = selectedId === item.id;
            return (
              <div className={`workspace-soundfont-item${isSelected ? " current" : ""}`} key={item.id}>
                <div className="workspace-soundfont-item__head">
                  <span className="workspace-soundfont-item__name">{item.name || "—"}</span>
                  {isSelected && <StatusBadge variant="success">当前</StatusBadge>}
                </div>
                <div className="workspace-soundfont-item__meta">
                  {item.format || "—"} · {item.size_bytes ? `${(item.size_bytes / 1024 / 1024).toFixed(1)} MB` : "—"}
                  {item.is_default ? " · 默认" : ""}
                </div>
                {item.path && <div className="workspace-soundfont-item__path">{item.path}</div>}
                {item.tags.length > 0 && <div className="workspace-soundfont-item__tags">{item.tags.map((t) => `#${t}`).join(" ")}</div>}
                <ButtonRow className="workspace-soundfont-item__actions">
                  <ActionButton
                    variant="secondary"
                    onClick={() => void sf.selectSoundfont(item.id)}
                    disabled={!hasSong || isSelected || sf.loading}
                    disabledReason={!hasSong ? "请先生成或导入工程" : undefined}
                  >
                    {isSelected ? "已选择" : "选择此音源"}
                  </ActionButton>
                  <ActionButton
                    variant="primary"
                    onClick={() => void sf.selectSoundfont(item.id)}
                    disabled={!hasSong || isSelected || sf.loading}
                    disabledReason={!hasSong ? "请先生成或导入工程" : isSelected ? "已应用该音源" : undefined}
                  >
                    应用到当前工程
                  </ActionButton>
                </ButtonRow>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <SectionCard title="SoundFont / 音源管理" description="扫描 / 选择 / 应用到工程">
      {body}
    </SectionCard>
  );
}

export default SoundfontPanel;

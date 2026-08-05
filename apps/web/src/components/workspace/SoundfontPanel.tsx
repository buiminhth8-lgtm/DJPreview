// 音源（SoundFont）面板：列表 / 扫描 / 项目选择 / missing 提示。

import { useEffect } from "react";

import { useSoundfonts } from "../../hooks";

export interface SoundfontPanelProps {
  songId: string;
  onError?: (message: string) => void;
}

export default function SoundfontPanel({ songId, onError }: SoundfontPanelProps) {
  const sf = useSoundfonts(songId);

  useEffect(() => {
    void sf.loadSoundfonts();
  }, [sf.loadSoundfonts]);

  useEffect(() => {
    if (songId) {
      void sf.loadProjectSoundfont();
    }
  }, [songId, sf.loadProjectSoundfont]);

  useEffect(() => {
    if (sf.error) onError?.(sf.error);
  }, [sf.error, onError]);

  const selectedId = sf.projectSoundfont?.soundfont?.soundfont_id ?? null;

  return (
    <section className="panel result">
      <h2>音源（SoundFont）</h2>
      {sf.projectSoundfont?.warning && <div className="warning">⚠ {sf.projectSoundfont.warning}</div>}
      <div className="actions">
        <button onClick={() => void sf.rescan()} disabled={sf.loading}>
          {sf.loading ? "扫描中…" : "重新扫描"}
        </button>
      </div>
      {sf.soundfonts.length === 0 && (
        <p className="muted-note">
          未找到音源。将合法的 .sf2 / .sf3 文件放入 <code>data/soundfonts/</code>（或
          <code> assets/soundfonts/</code>）后重新扫描。
        </p>
      )}
      {sf.soundfonts.length > 0 && (
        <div className="soundfont-list">
          {sf.soundfonts.map((item) => (
            <div
              className={`soundfont-item${selectedId === item.id ? " current" : ""}`}
              key={item.id}
            >
              <div className="soundfont-head">
                <span className="soundfont-name">{item.name}</span>
                <span className="soundfont-meta">
                  {item.format} · {(item.size_bytes / 1024 / 1024).toFixed(1)} MB
                  {item.is_default ? " · 默认" : ""}
                  {selectedId === item.id ? " · 当前" : ""}
                </span>
              </div>
              {item.tags.length > 0 && (
                <div className="soundfont-tags">{item.tags.map((tag) => `#${tag}`).join(" ")}</div>
              )}
              <button
                className="restore-btn"
                onClick={() => void sf.selectSoundfont(item.id)}
                disabled={selectedId === item.id}
              >
                {selectedId === item.id ? "已选择" : "选择此音源"}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ImportProjectButton：导入 .aimusic.zip（T33.3）。
// 只负责文件选择 + 调用 projectApi.importProject + 状态展示；
// 成功回调把新 songId 交给父级（刷新列表或跳转工作台）。

import { useRef, useState } from "react";
import { importProject } from "./projectApi";
import { ActionButton, InlineNotice } from "../../components/ui";

export interface ImportProjectButtonProps {
  variant?: "primary" | "secondary" | "ghost";
  onImported: (songId: string) => void | Promise<void>;
}

export function ImportProjectButton({ variant = "secondary", onImported }: ImportProjectButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File | undefined | null) => {
    if (!file || importing) return;
    setImporting(true);
    setError(null);
    try {
      const result = await importProject(file);
      await onImported(result.songId);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <span className="import-project">
      <ActionButton
        variant={variant}
        onClick={() => fileInputRef.current?.click()}
        loading={importing}
        disabled={importing}
      >
        {importing ? "正在导入…" : "导入工程"}
      </ActionButton>
      <input
        ref={fileInputRef}
        type="file"
        accept=".zip,.aimusic.zip,application/zip"
        style={{ display: "none" }}
        aria-label="选择 .aimusic.zip 工程文件导入"
        onChange={(e) => void handleFile(e.target.files?.[0])}
      />
      {error && (
        <InlineNotice variant="danger" title="导入失败">
          {error}
        </InlineNotice>
      )}
    </span>
  );
}

// ProjectWorkspacePage：/projects/:songId 工程工作台页（T33.1）。
// songId 必须来自 URL；缺失时显示错误状态，不崩溃。
// 复用 LegacyWorkspaceContent（原 App 工作台过渡），支持直接打开/刷新恢复。

import { Link, useParams } from "react-router-dom";
import LegacyWorkspaceContent from "../components/legacy/LegacyWorkspaceContent";
import { ErrorState } from "../components/ui";

export default function ProjectWorkspacePage() {
  const { songId } = useParams<{ songId: string }>();

  if (!songId) {
    return (
      <div className="page page--workspace">
        <ErrorState
          title="缺少工程 ID"
          message="URL 中没有有效的 songId（/projects/:songId）。"
          action={
            <Link to="/projects" className="ui-action-button ui-action-button--secondary">
              返回工程库
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="page page--workspace">
      <LegacyWorkspaceContent songId={songId} />
    </div>
  );
}

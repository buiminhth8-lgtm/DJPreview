// ProjectLibraryPage：/projects 工程库页（T33.1 页面壳）。
// 正式工程列表 / 搜索 / 导入 / 删除将在 T33.3 / T33.8 完善。

import { Link } from "react-router-dom";
import { EmptyState, SectionCard } from "../components/ui";

export default function ProjectLibraryPage() {
  return (
    <div className="page page--projects">
      <SectionCard title="工程库" description="历史工程列表与导入">
        <EmptyState
          title="工程库能力建设中"
          description="当前工程列表能力将在 T33.3 完善：支持历史工程入口、搜索、导入与删除。"
          action={
            <Link to="/create" className="ui-action-button ui-action-button--primary">
              去创作新音乐
            </Link>
          }
        />
      </SectionCard>
    </div>
  );
}

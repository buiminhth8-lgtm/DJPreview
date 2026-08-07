// NotFoundPage：未知路径（T33.1）。
// 最小错误页，不展示技术栈错误。

import { Link } from "react-router-dom";
import { EmptyState, ButtonRow } from "../components/ui";

export default function NotFoundPage() {
  return (
    <div className="page page--not-found">
      <EmptyState
        title="页面不存在"
        description="你访问的地址不存在或已被移动。"
        action={
          <ButtonRow>
            <Link to="/create" className="ui-action-button ui-action-button--primary">
              返回创作页
            </Link>
            <Link to="/projects" className="ui-action-button ui-action-button--secondary">
              返回工程库
            </Link>
          </ButtonRow>
        }
      />
    </div>
  );
}

// CreatePage：/create 创作页（T33.1 页面壳）。
// 复用 LegacyCreateContent（生成控制台 + 概览 + 调试），生成成功后跳转工作台。

import LegacyCreateContent from "../components/legacy/LegacyCreateContent";

export default function CreatePage() {
  return (
    <div className="page page--create">
      <LegacyCreateContent />
    </div>
  );
}

// App.tsx：T33.1 兼容层。
// main.tsx 已改为 RouterProvider（见 app/router.tsx）。
// 本组件保留旧单页行为（默认进入工作台），供兼容导入；页面入口请使用 CreatePage /
// ProjectLibraryPage / ProjectWorkspacePage。

import { Navigate } from "react-router-dom";

export default function App() {
  return <Navigate to="/create" replace />;
}

// app/router.tsx：T33.1 路由定义。
// 三路由结构：/create、/projects、/projects/:songId；/ 自动跳转 /create。

import { createBrowserRouter, Navigate } from "react-router-dom";

import AppShell from "./layout/AppShell";
import CreatePage from "../pages/CreatePage";
import NotFoundPage from "../pages/NotFoundPage";
import ProjectLibraryPage from "../pages/ProjectLibraryPage";
import ProjectWorkspacePage from "../pages/ProjectWorkspacePage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      {
        path: "/",
        element: <Navigate to="/create" replace />,
      },
      {
        path: "/create",
        element: <CreatePage />,
      },
      {
        path: "/projects",
        element: <ProjectLibraryPage />,
      },
      {
        path: "/projects/:songId",
        element: <ProjectWorkspacePage />,
      },
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
]);

// AppShell：顶层导航壳（T33.1）。
// 只负责导航与布局，不管理 song/project 业务状态。

import { NavLink, Outlet } from "react-router-dom";

export default function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <NavLink to="/create" className="app-shell__brand">
          AI Music
        </NavLink>
        <nav className="app-shell__nav" aria-label="主导航">
          <NavLink
            to="/create"
            className={({ isActive }) => `app-shell__link${isActive ? " app-shell__link--active" : ""}`}
          >
            创作
          </NavLink>
          <NavLink
            to="/projects"
            className={({ isActive }) => `app-shell__link${isActive ? " app-shell__link--active" : ""}`}
          >
            工程库
          </NavLink>
        </nav>
      </header>
      <main className="app-shell__main">
        <Outlet />
      </main>
    </div>
  );
}

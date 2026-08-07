import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./app/router";
import "./styles.css";
import "./styles/design-tokens.css";
import "./styles/workspace-ui.css";
import "./styles/workspace-layout.css";
import "./styles/workspace-results.css";
import "./styles/workspace-structure.css";
import "./styles/workspace-editing.css";
import "./styles/workspace-utilities.css";
import "./styles/workspace-responsive.css";
import "./styles/app-shell.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);

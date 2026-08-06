import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./styles/design-tokens.css";
import "./styles/workspace-ui.css";
import "./styles/workspace-layout.css";
import "./styles/workspace-results.css";
import "./styles/workspace-structure.css";
import "./styles/workspace-editing.css";
import "./styles/workspace-utilities.css";
import "./styles/workspace-responsive.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

// 后端地址：默认直连 http://localhost:8000（可通过 VITE_API_BASE_URL 覆盖）
// 同时提供 /api 代理，方便不使用环境变量时的本地开发。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});

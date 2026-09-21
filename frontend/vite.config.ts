// Vite entry; local API traffic is proxied to Django.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: "127.0.0.1",
    port: 5173,

    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },

      // Grafana는 React SPA fallback으로 보내면 안 된다.
      // 반드시 로컬 SYSTEM_ADMIN Auth Gateway를 경유한다.
      "/grafana": {
        target: "http://127.0.0.1:3002",
        changeOrigin: false,
        secure: false,
        ws: true,
      },
    },
  },
});

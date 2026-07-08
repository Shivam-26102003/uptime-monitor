import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev (npm run dev) we proxy /api -> backend so the browser talks to a single
// origin, mirroring how nginx proxies it in the Docker build.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});

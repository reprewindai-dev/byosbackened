import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    cors: true,
    proxy: {
      "/api": {
        target: process.env.VITE_UACP_BACKEND_BASE_URL || "https://api.veklom.com",
        changeOrigin: true,
        secure: true,
      },
      "/v1/exec": {
        target: process.env.VITE_UACP_BACKEND_BASE_URL || "https://api.veklom.com",
        changeOrigin: true,
        secure: true,
      },
      "/status": {
        target: process.env.VITE_UACP_BACKEND_BASE_URL || "https://api.veklom.com",
        changeOrigin: true,
        secure: true,
      },
      "/health": {
        target: process.env.VITE_UACP_BACKEND_BASE_URL || "https://api.veklom.com",
        changeOrigin: true,
        secure: true,
      },
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "workspace-assets",
    sourcemap: false,
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes("node_modules/react") ||
            id.includes("node_modules/react-dom") ||
            id.includes("node_modules/react-router-dom")
          ) {
            return "react";
          }
          if (id.includes("node_modules/@tanstack/react-query")) {
            return "query";
          }
          if (id.includes("node_modules/recharts")) {
            return "charts";
          }
          return undefined;
        },
      },
    },
  },
});

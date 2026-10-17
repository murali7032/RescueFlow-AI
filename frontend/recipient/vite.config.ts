import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { apiProxy } from "../shared/vite-proxy";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@foodbridge/shared": path.resolve(__dirname, "../shared") },
  },
  server: {
    port: 5174,
    host: true,
    proxy: { ...apiProxy },
  },
  test: { environment: "jsdom", globals: true },
});

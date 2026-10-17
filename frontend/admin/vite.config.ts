import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@foodbridge/shared": path.resolve(__dirname, "../shared") },
  },
  server: { port: 5175 },
  test: { environment: "jsdom", globals: true },
});

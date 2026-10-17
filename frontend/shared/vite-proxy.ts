/** Shared Vite dev-server proxy for Cloud Shell + local same-origin API calls. */
export const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
  "/health": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
} as const;

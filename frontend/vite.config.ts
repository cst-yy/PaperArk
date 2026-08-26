import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: "0.0.0.0",
      watch: {
        // A second Vite process (for example a production build running while
        // the dev container is up) briefly creates this bundled-config file.
        // On Docker Desktop's Windows bind mount, watching that transient path
        // can raise EIO after it is removed and terminate the dev server.
        ignored: [
          "**/vite.config.*.timestamp-*.mjs",
          "**/dist*/**",
        ],
      },
      proxy: {
        "/api": {
          // Local `npm run dev` uses localhost by default. Docker Compose sets
          // VITE_API_PROXY_TARGET=http://backend:8000 for its network alias.
          target: env.VITE_API_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
  };
});

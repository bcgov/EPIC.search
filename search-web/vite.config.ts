import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import istanbul from "vite-plugin-istanbul";

// https://vitejs.dev/config/

export default defineConfig({
  plugins: [
    TanStackRouterVite(),
    react(),
    istanbul({
      cypress: true,
      requireEnv: false,
    }),
  ],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 3000,
    strictPort: false, // Allow Vite to use next available port if 3000 is busy
    open: true, // Automatically open browser
    proxy: {
      '/api': {
        target: process.env.PROXY_API_URL || 'http://127.0.0.1:8081',
        changeOrigin: true,
        secure: false
      }
    }
  },
});

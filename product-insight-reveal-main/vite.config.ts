// @ts-ignore: Vite config uses Node.js and ESM imports
import { defineConfig } from "vite";
// @ts-ignore: Vite config uses plugin imports
import react from "@vitejs/plugin-react-swc";
// @ts-ignore: Node.js import
import path from "path";
// @ts-ignore: Custom plugin import
import { componentTagger } from "lovable-tagger";
// @ts-ignore: Node.js import
import { fileURLToPath } from 'url';

// Polyfill __dirname for ESM
// @ts-ignore: import.meta.url is valid in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// https://vitejs.dev/config/
export default defineConfig(({ mode }: { mode: string }) => ({
  base: './', // Ensure correct asset paths for nginx
  server: mode === 'development' ? {
    host: "::",
    port: 8080,
    proxy: {
      "/scrape": "http://localhost:8000",
      "/bulk-csv": "http://localhost:8000",
      "/health": "http://localhost:8000"
    },
  } : undefined,
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: 'dist', // Default, but explicit for clarity
  },
}));

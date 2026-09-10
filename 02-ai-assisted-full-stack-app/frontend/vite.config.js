import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The frontend calls the FastAPI backend at /api/*. In dev, Vite proxies those
// requests to the backend so the browser makes same-origin calls and CORS is a
// non-issue no matter which host/IP the dev server is reached on. Override the
// target with VITE_BACKEND_URL (see .env.example).
const BACKEND_URL = process.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // bind 0.0.0.0 so the dev server is reachable by the machine's IP
    proxy: {
      '/api': { target: BACKEND_URL, changeOrigin: true },
    },
  },
})

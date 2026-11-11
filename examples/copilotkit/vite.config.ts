import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The formguide demo server (backend/demo) provides /agent (the agent) and /java (a mock form backend).
export default defineConfig({
  plugins: [react()],
  server: { port: 5174, proxy: { '/agent': 'http://localhost:8000', '/java': 'http://localhost:8000' } },
})

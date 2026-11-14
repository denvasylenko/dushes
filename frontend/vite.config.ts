import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The chat widget is used from its sources in this repository (packages/agui-chat), so the demo
// always runs the current widget. An app outside the repo installs @formguide/agui-chat instead.
const widget = fileURLToPath(new URL('../packages/agui-chat/src', import.meta.url))

export default defineConfig({
  plugins: [react()],
  // two pages: the form demo (index.html) and the multi-page site demo (site.html)
  build: { rollupOptions: { input: { main: 'index.html', site: 'site.html' } } },
  resolve: {
    dedupe: ['react', 'react-dom'],   // one React, also for the widget sources
    alias: [
      { find: /^@formguide\/agui-chat\/formguide$/, replacement: `${widget}/formguide/index.ts` },
      { find: /^@formguide\/agui-chat\/react$/, replacement: `${widget}/react.ts` },
      { find: /^@formguide\/agui-chat\/highlight$/, replacement: `${widget}/highlight.ts` },
      { find: /^@formguide\/agui-chat$/, replacement: `${widget}/index.ts` },
    ],
  },
  server: {
    port: 5173,
    proxy: {
      '/java': 'http://127.0.0.1:8000',
      '/agent': 'http://127.0.0.1:8000',
      '/site': 'http://127.0.0.1:8000',
    },
  },
})

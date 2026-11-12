import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The widget comes from its sources in this repository; an app outside it installs @formguide/agui-chat.
const widget = fileURLToPath(new URL('../../packages/agui-chat/src', import.meta.url))

export default defineConfig({
  base: '/examples/react-hook-form/',   // served by the demo server after `npm run build`
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: [
      { find: /^@formguide\/agui-chat\/react-hook-form$/, replacement: `${widget}/rhf.ts` },
      { find: /^@formguide\/agui-chat\/react$/, replacement: `${widget}/react.ts` },
      { find: /^@formguide\/agui-chat$/, replacement: `${widget}/index.ts` },
    ],
  },
  server: { port: 5175, proxy: { '/agent': 'http://localhost:8000' } },
})

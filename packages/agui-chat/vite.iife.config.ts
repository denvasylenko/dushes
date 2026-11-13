import { defineConfig } from 'vite'
import { minifyCss } from './scripts/minify-css.mjs'

// One self-registering script for a <script> tag: the element plus the formguide plugin,
// exposed as window.AguiChat.
export default defineConfig({
  plugins: [minifyCss()],
  // language packs: agui-chat.lang-<lang>.js files next to this script (scripts/lang-files.mjs)
  resolve: { alias: { '#lang-loader': new URL('./src/lang-loader.iife.ts', import.meta.url).pathname,
    '#theme-loader': new URL('./src/theme-loader.iife.ts', import.meta.url).pathname,
    '#editor-loader': new URL('./src/editor-loader.iife.ts', import.meta.url).pathname } },
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/standalone.ts', name: 'AguiChat', formats: ['iife'], fileName: () => 'agui-chat.iife.js' },
  },
})

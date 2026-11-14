import { defineConfig } from 'vite'
import { minifyCss } from './scripts/minify-css.mjs'

// The shortcut tooltip as its own script for the one-script build: dist/agui-chat.tip.js, loaded on the first hover.
export default defineConfig({
  plugins: [minifyCss()],
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/tip.ts', name: 'AguiChatTip', formats: ['iife'], fileName: () => 'agui-chat.tip.js' },
  },
})

import { defineConfig } from 'vite'
import { minifyCss } from './scripts/minify-css.mjs'

// The experimental voice mode as its own script for the one-script build: dist/agui-chat.voice.js, fetched only by a
// chat whose host turned voice on (<agui-chat voice>).
export default defineConfig({
  plugins: [minifyCss()],
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/voice.ts', name: 'AguiChatVoice', formats: ['iife'], fileName: () => 'agui-chat.voice.js' },
  },
})

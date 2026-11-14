import { defineConfig } from 'vite'

// The field highlight as its own script for the one-script build: dist/agui-chat.highlight.js, loaded on first use.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/highlight.ts', name: 'AguiChatHighlight', formats: ['iife'], fileName: () => 'agui-chat.highlight.js' },
  },
})

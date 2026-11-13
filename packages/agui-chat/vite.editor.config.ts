import { defineConfig } from 'vite'

// The markup editor as its own script for the one-script build: dist/agui-chat.editor.js, loaded on demand.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/editor.ts', name: 'AguiChatEditor', formats: ['iife'], fileName: () => 'agui-chat.editor.js' },
  },
})

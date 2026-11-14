import { defineConfig } from 'vite'

// The image view and the markup editor as their own script for the one-script build: dist/agui-chat.editor.js, loaded on demand.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/media.ts', name: 'AguiChatEditor', formats: ['iife'], fileName: () => 'agui-chat.editor.js' },
  },
})

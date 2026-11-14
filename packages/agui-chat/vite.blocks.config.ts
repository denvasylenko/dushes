import { defineConfig } from 'vite'

// The card blocks as their own script for the one-script build: dist/agui-chat.blocks.js, loaded on demand.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/formguide/blocks-entry.ts', name: 'AguiChatBlocks', formats: ['iife'], fileName: () => 'agui-chat.blocks.js' },
  },
})

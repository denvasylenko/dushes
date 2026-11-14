import { defineConfig } from 'vite'

// The card blocks as their own script for the one-script build: dist/agui-chat.blocks.js, loaded on demand.
export default defineConfig({
  // the charts in a card load Chart.js as one more script (agui-chat.charts.js), not inside this one
  resolve: { alias: { '#charts-loader': new URL('./src/charts-loader.iife.ts', import.meta.url).pathname } },
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/formguide/blocks-entry.ts', name: 'AguiChatBlocks', formats: ['iife'], fileName: () => 'agui-chat.blocks.js' },
  },
})

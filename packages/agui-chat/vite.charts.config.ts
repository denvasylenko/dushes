import { defineConfig } from 'vite'
import { chartjsLicence } from './scripts/chartjs-licence.mjs'

// Chart.js and its drawing as their own script for the one-script build: dist/agui-chat.charts.js, loaded on demand.
export default defineConfig({
  plugins: [chartjsLicence()],
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/formguide/chart-draw.ts', name: 'AguiChatCharts', formats: ['iife'], fileName: () => 'agui-chat.charts.js' },
  },
})

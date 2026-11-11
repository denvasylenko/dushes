import { defineConfig } from 'vite'

// One self-registering script for a <script> tag: the element plus the formguide plugin,
// exposed as window.AguiChat.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: true,
    lib: { entry: 'src/standalone.ts', name: 'AguiChat', formats: ['iife'], fileName: () => 'agui-chat.iife.js' },
  },
})

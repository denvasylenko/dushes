import { defineConfig } from 'vite'

// ES modules for bundlers: the element, the formguide plugin and the React wrapper.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
    lib: {
      entry: { 'agui-chat': 'src/index.ts', formguide: 'src/formguide/index.ts', react: 'src/react.ts', 'react-hook-form': 'src/rhf.ts' },
      formats: ['es'],
    },
    rollupOptions: { external: ['react', 'react/jsx-runtime'] },
  },
  test: { environment: 'happy-dom' },
} as never)

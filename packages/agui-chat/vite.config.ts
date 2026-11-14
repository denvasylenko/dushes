import { defineConfig } from 'vite'
import { minifyCss } from './scripts/minify-css.mjs'
import { chartjsLicence } from './scripts/chartjs-licence.mjs'

// ES modules for bundlers: the element, the formguide plugin and the React wrapper.
export default defineConfig({
  plugins: [minifyCss(), chartjsLicence()],
  // language packs: chunks loaded with import() (the one-script build swaps in a <script> loader)
  resolve: { alias: { '#lang-loader': new URL('./src/lang-loader.ts', import.meta.url).pathname,
    '#theme-loader': new URL('./src/theme-loader.ts', import.meta.url).pathname,
    '#tip-loader': new URL('./src/tip-loader.ts', import.meta.url).pathname,
    '#editor-loader': new URL('./src/editor-loader.ts', import.meta.url).pathname,
    '#blocks-loader': new URL('./src/blocks-loader.ts', import.meta.url).pathname,
    '#charts-loader': new URL('./src/charts-loader.ts', import.meta.url).pathname } },
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

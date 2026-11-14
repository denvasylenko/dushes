/**
 * The Vue stands, one page each (stands/<name>/index.html), built to dist/ and served next to the e2e fixtures.
 * `@formguide/agui-chat/vue` is the package's Vue adapter when it exists (packages/agui-chat/src/vue.ts); until then
 * the stands get src/adapter-pending.ts, which says so, and the checks fail by design. STAND_ADAPTER=reference builds
 * them with QA's reference adapter (src/reference-adapter.ts: the agreed contract) to check the stands themselves.
 */
import { existsSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import vue from '@vitejs/plugin-vue'
import { quasar, transformAssetUrls } from '@quasar/vite-plugin'
import { defineConfig } from 'vite'

const pkg = resolve(__dirname, '../../packages/agui-chat/src')
const official = resolve(pkg, 'vue.ts')
const adapter = process.env.STAND_ADAPTER === 'reference' ? resolve(__dirname, 'src/reference-adapter.ts')
  : existsSync(official) ? official : resolve(__dirname, 'src/adapter-pending.ts')
const only = (process.env.STAND_ONLY || '').split(',').filter(Boolean)   // build these stands only (parallel authors)
const stands = Object.fromEntries(readdirSync(resolve(__dirname, 'stands')).filter((d) => existsSync(resolve(__dirname, 'stands', d, 'index.html')))
  .filter((d) => !only.length || only.includes(d))
  .map((d) => [d, resolve(__dirname, 'stands', d, 'index.html')]))

export default defineConfig({
  base: './',
  plugins: [vue({ template: { transformAssetUrls, compilerOptions: { isCustomElement: (t) => t === 'agui-chat' } } }), quasar()],
  resolve: {
    alias: [
      { find: '@formguide/agui-chat/vue', replacement: adapter },
      { find: '@formguide/agui-chat/formguide', replacement: resolve(pkg, 'formguide/index.ts') },
      { find: '@formguide/agui-chat/highlight', replacement: resolve(pkg, 'highlight.ts') },
      { find: '@formguide/agui-chat/schema', replacement: resolve(pkg, 'formguide/schema.ts') },
      { find: /^@formguide\/agui-chat$/, replacement: resolve(pkg, 'index.ts') },
    ],
  },
  build: { outDir: process.env.STAND_OUT || (process.env.STAND_ADAPTER === 'reference' ? 'dist-reference' : 'dist'), emptyOutDir: true, rollupOptions: { input: stands } },
  define: { __ADAPTER__: JSON.stringify(adapter.includes('reference') ? 'reference' : adapter.includes('pending') ? 'pending' : 'official') },
})

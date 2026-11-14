/**
 * The Nuxt 3 stand of the Vue benchmark: the same form as stands/reactive, rendered on the server. The chat is
 * client-only (a custom element); the adapter must not touch window or document during SSR. STAND_ADAPTER=reference
 * builds it with QA's reference adapter, else the package's (packages/agui-chat/src/vue.ts) or the pending stub.
 */
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

const pkg = resolve(__dirname, '../../packages/agui-chat/src')
const official = resolve(pkg, 'vue.ts')
const adapter = process.env.STAND_ADAPTER === 'reference' ? resolve(__dirname, '../vue/src/reference-adapter.ts')
  : existsSync(official) ? official : resolve(__dirname, '../vue/src/adapter-pending.ts')

export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  ssr: true,
  devtools: { enabled: false },
  vue: { compilerOptions: { isCustomElement: (t) => t === 'agui-chat' } },
  vite: {
    resolve: {
      alias: [
        { find: '@formguide/agui-chat/vue', replacement: adapter },
        { find: '@formguide/agui-chat/formguide', replacement: resolve(pkg, 'formguide/index.ts') },
        { find: '@formguide/agui-chat/highlight', replacement: resolve(pkg, 'highlight.ts') },
        { find: '@formguide/agui-chat/schema', replacement: resolve(pkg, 'formguide/schema.ts') },
        { find: /^@formguide\/agui-chat$/, replacement: resolve(pkg, 'index.ts') },
      ],
    },
    define: { __ADAPTER__: JSON.stringify(adapter.includes('reference') ? 'reference' : adapter.includes('pending') ? 'pending' : 'official') },
  },
})

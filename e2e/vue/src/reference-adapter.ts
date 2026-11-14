/**
 * QA's reference implementation of the agreed Vue adapter contract (not the package's): it checks the stands and the
 * tests while the real one is built. Contract (Design, 2026-11-14):
 *   const { plugins, ready, error, bridge } = useFormguide(source, schema, { url, onReveal, getUi, plugin, validate, errors })
 *   source: a reactive object, a ref, a Pinia store, or { getValues, setValue }; plugins/ready/error are refs.
 *   After every write: nextTick twice, then `validate` (VeeValidate validate(), Vuelidate $validate()), then the config.
 *   "Take me there": highlight by data-name, searched in document at call time (Teleport works); onReveal may be async.
 *   Undo goes through the same apply + settle.
 */
import { isRef, nextTick, onMounted, ref, toRaw, type Ref } from 'vue'
import { formguide, type FormguideOptions } from '@formguide/agui-chat/formguide'
import { highlightField, lookAt } from '@formguide/agui-chat/highlight'   // SSR-safe since c184c96
import { schemaForm, type FormSchema, type Values } from '@formguide/agui-chat/schema'
import type { Plugin } from '@formguide/agui-chat'

export interface Access { getValues: () => Values; setValue: (name: string, value: unknown) => void }
export interface Options {
  url?: string
  onReveal?: (section: string) => void | Promise<void>
  getUi?: () => Record<string, unknown>
  plugin?: Partial<FormguideOptions>
  validate?: () => Promise<Record<string, string> | boolean | { valid: boolean }>   // VeeValidate's {valid, errors} as it is
  errors?: () => Record<string, string>
}

const plain = (v: unknown): unknown => JSON.parse(JSON.stringify(toRaw(v) ?? null))

/** Reads and writes dotted paths ("items.2.qty") in a reactive object, a ref or a store. */
export function access(source: unknown): Access {
  if (source && typeof (source as Access).getValues === 'function') return source as Access
  const root = () => (isRef(source) ? (source as Ref<Record<string, unknown>>).value
    : (source as { $state?: Record<string, unknown> })?.$state ?? source) as Record<string, unknown>   // a Pinia store: its $state
  const get = (o: unknown, path: string[]): unknown => path.reduce<unknown>((x, k) => (x as Record<string, unknown>)?.[k], o)
  return {
    getValues: () => plain(root()) as Values,
    setValue: (name, value) => {
      const path = name.split('.'), last = path.pop()!
      const parent = get(root(), path) as Record<string, unknown>
      parent[last] = value
    },
  }
}

export function useFormguide(source: unknown, schema: FormSchema, opts: Options = {}) {
  const a = access(source)
  const bridge = schemaForm(schema, { getValues: a.getValues, setValue: a.setValue, getErrors: () => opts.errors?.() ?? {} })
  const plugins = ref<Plugin[]>([]), ready = ref(false), error = ref<string | null>(null)
  const url = opts.url ?? '/agent/run', base = url.replace(/\/run\/?$/, '')
  const settle = async () => {
    await nextTick(); await nextTick()
    if (opts.validate) await opts.validate()
  }
  onMounted(async () => {   // never during SSR
    try {
      const r = await fetch(`${base}/layouts`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsx: bridge.jsx, form_id: schema.id, ...(schema.domain ? { domain: schema.domain } : {}), config: bridge.config() }) })
      if (!r.ok) throw new Error(`layout registration failed: HTTP ${r.status}`)
      const hash = (await r.json()).jsx_hash as string
      plugins.value = [formguide({
        getState: () => ({ config: bridge.config(), jsx_hash: hash, form_id: schema.id,
                           ui: opts.getUi?.() ?? { focused: (document.activeElement as HTMLInputElement | null)?.name ?? null } }),
        applyChanges: async (changes) => { await bridge.apply(changes); await settle(); return bridge.config() },   // apply maps choices (valueAs)
        onDirective: async (d) => {
          const s = bridge.sectionOf(d.target)
          if (s) await opts.onReveal?.(s)
          await nextTick()
          lookAt(d.target, d.hint); for (const n of d.also ?? []) highlightField(n, { kind: 'look' })
        },
        ...opts.plugin,
      })]
      ready.value = true
    } catch (e) { error.value = e instanceof Error ? e.message : String(e) }
  })
  return { plugins, ready, error, bridge }
}

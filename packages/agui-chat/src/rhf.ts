/**
 * react-hook-form + formguide in one hook.
 *
 *   const form = useForm<LoanForm>()
 *   const { plugins, ready } = useFormguide(form, schema, { onReveal: (section) => setTab(section) })
 *   return <>
 *     <form>...<input {...form.register('first_name')} />...</form>
 *     {ready && <AguiChat url="/agent/run" plugins={plugins} />}
 *   </>
 *
 * The form object is used structurally (getValues, setValue, formState.errors), so this entry does not
 * import react-hook-form; any library with the same three members works.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { formguide, type FormguideOptions } from './formguide/index'
import { lookAt } from './formguide/hint'
import { schemaForm, type FormSchema, type SchemaBridge, type Values } from './formguide/schema'
import type { Plugin } from './types'

export type { FormSchema, FieldSchema, SectionSchema, Option } from './formguide/schema'
export { schemaForm } from './formguide/schema'

/** The part of react-hook-form's UseFormReturn the hook uses. */
export interface FormLike {
  getValues: () => Values
  setValue: (name: string, value: unknown, options?: { shouldDirty?: boolean; shouldValidate?: boolean; shouldTouch?: boolean }) => void
  formState: { errors: Record<string, unknown> }
}

export interface UseFormguideOptions {
  /** The run URL (default /agent/run); the router's other endpoints are next to it. */
  url?: string
  /** Where formguide's router is mounted, when it is not the run URL without /run. */
  baseUrl?: string
  /** Open the section (tab, step) a field is in before it is shown. */
  onReveal?: (section: string) => void
  /** What the user sees right now; default: the focused field. */
  getUi?: () => Record<string, unknown>
  /** Passed through to the formguide plugin (fieldCard, undoSeconds, ...). */
  plugin?: Partial<FormguideOptions>
}

export interface UseFormguide {
  plugins: Plugin[]
  /** True once the layout is registered: render the chat then. */
  ready: boolean
  error: string | null
  bridge: SchemaBridge
}

/** react-hook-form's nested errors -> {"a.b": message}. */
export function flatErrors(errors: Record<string, unknown> | undefined, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(errors ?? {})) {
    if (!v || typeof v !== 'object') continue
    const e = v as { message?: unknown; type?: unknown }
    if (typeof e.message === 'string' || typeof e.type === 'string') out[prefix + k] = String(e.message || e.type)
    else Object.assign(out, flatErrors(v as Record<string, unknown>, `${prefix}${k}.`))
  }
  return out
}

const base = (url: string, baseUrl?: string) => (baseUrl ?? url.replace(/\/run\/?$/, '')).replace(/\/$/, '')

export function useFormguide(form: FormLike, schema: FormSchema, opts: UseFormguideOptions = {}): UseFormguide {
  const ref = useRef({ form, opts })
  ref.current = { form, opts }
  const key = JSON.stringify(schema, (_k, v) => (typeof v === 'function' ? String(v) : v))
  const bridge = useMemo(() => schemaForm(schema, {
    getValues: () => ref.current.form.getValues(),
    setValue: (name, value) => ref.current.form.setValue(name, value, { shouldDirty: true, shouldValidate: true, shouldTouch: true }),
    getErrors: () => flatErrors(ref.current.form.formState.errors),
  }), [key]) // eslint-disable-line react-hooks/exhaustive-deps
  const [hash, setHash] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const url = opts.url ?? '/agent/run'

  useEffect(() => {
    let live = true
    setHash(null)
    setError(null)
    fetch(`${base(url, opts.baseUrl)}/layouts`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsx: bridge.jsx, form_id: schema.id, ...(schema.domain ? { domain: schema.domain } : {}), config: bridge.config() }),
    }).then(async (r) => {
      if (!r.ok) throw new Error(`layout registration failed: HTTP ${r.status}`)
      const d = await r.json()
      for (const w of d.warnings ?? []) console.warn(`formguide: ${w}`)
      if (live) setHash(d.jsx_hash)
    }).catch((e) => { if (live) setError(e instanceof Error ? e.message : String(e)) })
    return () => { live = false }
  }, [bridge, url, opts.baseUrl, schema.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const plugins = useMemo(() => hash ? [formguide({
    getState: () => {
      const focused = (document.activeElement as HTMLInputElement | null)?.name
      const ui = ref.current.opts.getUi?.() ?? { focused: focused && bridge.fields.has(focused) ? focused : null }
      return { config: bridge.config(), jsx_hash: hash, form_id: schema.id, ui }
    },
    applyChanges: (changes) => bridge.apply(changes),
    onDirective: (d) => {
      const s = bridge.sectionOf(d.target)
      if (s) ref.current.opts.onReveal?.(s)
      setTimeout(() => lookAt(d.target, d.hint), 60)   // after the section opens: scroll, focus, ring, hint
    },
    ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}),
    ...opts.plugin,
  })] : [], [hash, bridge]) // eslint-disable-line react-hooks/exhaustive-deps

  return { plugins, ready: !!hash, error, bridge }
}

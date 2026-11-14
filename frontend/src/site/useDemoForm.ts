import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { javaEvent, javaForm, registerLayout, type FormState } from '../api'
import { parseJsx } from '../jsx'
import type { Config, JsxNode, RevealStep, UiDirective, UiState } from '../types'
import { highlightField } from '@formguide/agui-chat/highlight'

/** One demo form on a site page: loaded from the mock form backend, its values kept per browser
 * (stands in for the form backend's own persistence), and the hooks the chat needs. */
export type DemoForm = { formId: string; title: string; tree: JsxNode; hash: string }

const EMPTY_UI: UiState = { activeTabs: {}, openAccordions: [], focused: null }
const store = {
  get<T>(k: string): T | null { try { const v = localStorage.getItem(k); return v ? (JSON.parse(v) as T) : null } catch { return null } },
  set(k: string, v: unknown): void { try { localStorage.setItem(k, JSON.stringify(v)) } catch { /* no storage: still works */ } },
}

export function useDemoForm(formId: string | null) {
  const [form, setForm] = useState<DemoForm | null>(null)
  const [config, setConfig] = useState<Config | null>(null)
  const [ui, setUi] = useState<UiState>(EMPTY_UI)
  const [failed, setFailed] = useState(false)
  const cfgRef = useRef(config); cfgRef.current = config
  const uiRef = useRef(ui); uiRef.current = ui
  const formRef = useRef(form); formRef.current = form
  const reqId = useRef(0)
  const debounce = useRef<number | undefined>(undefined)

  useEffect(() => {
    setForm(null); setConfig(null); setFailed(false)
    if (!formId) return
    let live = true
    javaForm(formId).then(async (f) => {
      const hash = await registerLayout(f.jsx, f.form_id, f.domain, f.config)
      const saved = store.get<Config['state']>(`site:state:${f.form_id}`)
      const cfg = saved ? await javaEvent(f.form_id, saved, {}) : f.config
      if (!live) return
      const title = (f.domain?.title as string) ?? f.form_id.replace(/[_-]+/g, ' ').replace(/^./, (c: string) => c.toUpperCase())
      setForm({ formId: f.form_id, title, tree: parseJsx(f.jsx), hash })
      setConfig(cfg)
      setUi(store.get<UiState>(`site:ui:${f.form_id}`) ?? EMPTY_UI)
    }).catch(() => live && setFailed(true))
    return () => { live = false }
  }, [formId])

  useEffect(() => { if (form && config) store.set(`site:state:${form.formId}`, config.state) }, [form, config])
  useEffect(() => { if (form) store.set(`site:ui:${form.formId}`, { ...ui, focused: null }) }, [form, ui])

  const push = useCallback(async (changes: Record<string, unknown>) => {
    const id = ++reqId.current
    const next = await javaEvent(formRef.current!.formId, cfgRef.current!.state, changes)
    if (id === reqId.current) setConfig(next)
    cfgRef.current = next
    return next
  }, [])

  const setValue = useCallback((name: string, value: unknown, immediate: boolean) => {
    setConfig((c) => (c ? { ...c, state: { ...c.state, [name]: value } } : c))
    window.clearTimeout(debounce.current)
    if (immediate) void push({ [name]: value })
    else debounce.current = window.setTimeout(() => void push({}), 400)
  }, [push])

  const reveal = useCallback((steps: RevealStep[]) => setUi((u) => {
    const activeTabs = { ...u.activeTabs }
    let open = [...u.openAccordions]
    for (const s of steps) {
      if (s.type === 'tab') activeTabs[s.tabs] = s.tab
      else open = [...open.filter((a) => a !== s.name), s.name]
    }
    return { ...u, activeTabs, openAccordions: open }
  }), [])

  const applyDirective = useCallback((d: UiDirective) => {
    reveal(d.reveal)
    // the widget's own "look here" (@formguide/agui-chat/highlight), after the tab opens
    window.setTimeout(() => {
      highlightField(d.target, { kind: 'look', hint: d.hint })
      for (const n of d.also ?? []) highlightField(n, { kind: 'look' })
    }, 60)
  }, [reveal])

  /** The form as the backend last built it, for the run's state (pending typing pushed first). */
  const getState = useCallback(async (): Promise<FormState | null> => {
    const f = formRef.current
    if (!f || !cfgRef.current) return null
    window.clearTimeout(debounce.current)
    const cfg = await push({})
    return { config: cfg, jsx_hash: f.hash, form_id: f.formId, ui: { ...uiRef.current, now: new Date().toISOString().slice(0, 16) } }
  }, [push])

  const ctx = useMemo(() => (config ? {
    config, ui, setValue,
    setTab: (tabs: string, tab: string) => setUi((u) => ({ ...u, activeTabs: { ...u.activeTabs, [tabs]: tab } })),
    toggleAccordion: (name: string) => setUi((u) => ({ ...u, openAccordions: u.openAccordions.includes(name)
      ? u.openAccordions.filter((a) => a !== name) : [...u.openAccordions, name] })),
    setFocused: (name: string | null) => setUi((u) => ({ ...u, focused: name })),
  } : null), [config, ui, setValue])

  return { form, ctx, failed, getState, applyChanges: push, applyDirective }
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { formguide } from '@formguide/agui-chat/formguide'
import { Select } from './controls'
import { AguiChat } from '@formguide/agui-chat/react'
import type { AguiChatElement } from '@formguide/agui-chat'
import { javaEvent, javaForm, javaForms, registerLayout, FRONTEND_TOOLS, type FormState } from './api'
import { FormProvider, Render, type Highlight } from './Form'
import { parseJsx } from './jsx'
import Manager from './Manager'
import type { Config, JsxNode, RevealStep, UiDirective, UiState } from './types'

type AgentCtx = { text: string; stats: { context_tokens: number; config_tokens: number } } | null

/** The server's numbers for the last run (CUSTOM run_stats). */
type RunStats = { ttft_ms: number | null; total_ms: number; model_ms: number; tool_ms: number; tools: unknown[];
  tokens: { input: number | null; output: number | null }; cache_hit_rate: number | null } | null

/** Served under /demo/ on the public docs host: a way back to the docs, and no document uploads (they are off there). */
const HOSTED = import.meta.env.BASE_URL !== '/'
const sec = (ms: number | null) => (ms == null ? '-' : `${(ms / 1000).toFixed(1)} s`)

type LoadedForm = { formId: string; jsx: string; tree: JsxNode; hash: string; title: string }

const EMPTY_UI: UiState = { activeTabs: {}, openAccordions: [], focused: null }

/** The chat's language (UI and dictation); '' = the browser's. */
const LANGS: [string, string][] = [['', 'Auto'], ['en', 'English'], ['ru', 'Russian'], ['uk', 'Ukrainian'], ['de', 'German'],
  ['fr', 'French'], ['it', 'Italian'], ['es', 'Spanish']]

/** Data a host app may already have about the user: the demo's "Prefill from profile" button sends it. */
const PROFILES: Record<string, Record<string, unknown>> = {
  loan_application: {
    last_name: 'Smith', first_name: 'Anna', birth_date: '1990-04-12', gender: 'Female',
    email: 'anna.smith@example.com', phone_mobile: '+7 900 123 45 67', consent_pd: true,
  },
  barber_booking: { client_name: 'Anna Smith', client_phone: '+7 900 123 45 67' },
}

// Per-viewer persistence in the browser. The thread id is what brings the conversation back;
// form values and open sections stand in for what the real form backend would persist.
const store = {
  get<T>(key: string): T | null {
    try {
      const v = localStorage.getItem(key)
      return v ? (JSON.parse(v) as T) : null
    } catch {
      return null
    }
  },
  set(key: string, value: unknown): void {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch {
      /* storage unavailable: the page still works, it just will not remember */
    }
  },
}

function localNow(): string {
  const d = new Date()
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  const date = d.toLocaleDateString('sv-SE') // YYYY-MM-DD
  const day = d.toLocaleDateString('en-US', { weekday: 'long' })
  return `${date} ${day} ${d.toTimeString().slice(0, 5)} (${tz})`
}

/** The frontend tool the demo offers the agent, in the widget's format. */
const TOOLS = FRONTEND_TOOLS.map(({ name, description, parameters, run }) => ({ name, description, parameters, handler: (args: Record<string, unknown>) => run(args) }))

export default function App() {
  const [forms, setForms] = useState<string[]>([])
  const [formId, setFormId] = useState('loan_application')
  const [form, setForm] = useState<LoadedForm | null>(null)
  const [config, setConfig] = useState<Config | null>(null)
  const [ui, setUi] = useState<UiState>(EMPTY_UI)
  const [highlight, setHighlight] = useState<Highlight>(null)
  const [agentCtx, setAgentCtx] = useState<AgentCtx>(null)
  const [showCtx, setShowCtx] = useState(false)
  const [runStats, setRunStats] = useState<RunStats>(null)
  const [busy, setBusy] = useState(false)
  const [thread, setThread] = useState('')
  const [lang, setLang] = useState(() => store.get<string>('formguide:chat-lang') ?? '')
  const [view, setView] = useState<'form' | 'manager'>('form')

  const cfgRef = useRef<Config | null>(null)
  cfgRef.current = config
  const uiRef = useRef(ui)
  uiRef.current = ui
  const formRef = useRef<LoadedForm | null>(null)
  formRef.current = form
  const chatRef = useRef<AguiChatElement | null>(null)
  const reqId = useRef(0)
  const debounce = useRef<number | undefined>(undefined)

  useEffect(() => {
    javaForms().then(setForms)
  }, [])

  // ------------------------------------------------------------ load: JSX once, config from the form backend
  useEffect(() => {
    setForm(null)
    javaForm(formId).then(async (f) => {
      // the frontend forwards the JSX, the domain pack and the initial config (checked for value formats) once
      const hash = await registerLayout(f.jsx, f.form_id, f.domain, f.config)
      // the pack's title, or the id in words: loan_application -> Loan application
      const title = (f.domain?.title as string) ?? f.form_id.replace(/[_-]+/g, ' ').replace(/^./, (c: string) => c.toUpperCase())
      // reopen: the same conversation, the saved form values and the sections that were open
      const threadId = store.get<string>(`formguide:thread:${f.form_id}`) ?? crypto.randomUUID()
      store.set(`formguide:thread:${f.form_id}`, threadId)
      const saved = store.get<Config['state']>(`formguide:state:${f.form_id}`)
      const cfg = saved ? await javaEvent(f.form_id, saved, {}) : f.config
      setForm({ formId: f.form_id, jsx: f.jsx, tree: parseJsx(f.jsx), hash, title })
      setConfig(cfg)
      setUi(store.get<UiState>(`formguide:ui:${f.form_id}`) ?? EMPTY_UI)
      setAgentCtx(null)
      setThread(threadId)
    })
  }, [formId])

  // remember form values and open sections (stands in for the form backend's persistence)
  useEffect(() => {
    if (form && config) store.set(`formguide:state:${form.formId}`, config.state)
  }, [form, config])
  useEffect(() => {
    if (form) store.set(`formguide:ui:${form.formId}`, { ...ui, focused: null })
  }, [form, ui])
  useEffect(() => store.set('formguide:chat-lang', lang), [lang])

  // ------------------------------------------------------------ form events -> form backend -> new config
  const pushToJava = useCallback(async (changes: Record<string, unknown>) => {
    const id = ++reqId.current
    const next = await javaEvent(formRef.current!.formId, cfgRef.current!.state, changes)
    if (id === reqId.current) setConfig(next)
    cfgRef.current = next
    return next
  }, [])

  const setValue = useCallback((name: string, value: unknown, immediate: boolean) => {
    setConfig((c) => (c ? { ...c, state: { ...c.state, [name]: value } } : c))
    window.clearTimeout(debounce.current)
    if (immediate) void pushToJava({ [name]: value })
    else debounce.current = window.setTimeout(() => void pushToJava({}), 400)
  }, [pushToJava])

  const setTab = useCallback((tabs: string, tab: string) =>
    setUi((u) => ({ ...u, activeTabs: { ...u.activeTabs, [tabs]: tab } })), [])
  const toggleAccordion = useCallback((name: string) =>
    setUi((u) => ({
      ...u,
      openAccordions: u.openAccordions.includes(name)
        ? u.openAccordions.filter((a) => a !== name)
        : [...u.openAccordions, name],
    })), [])
  const setFocused = useCallback((name: string | null) => setUi((u) => ({ ...u, focused: name })), [])

  // ------------------------------------------------------------ UI directives from the agent
  const reveal = useCallback((steps: RevealStep[]) => {
    setUi((u) => {
      const activeTabs = { ...u.activeTabs }
      let open = [...u.openAccordions]
      for (const s of steps) {
        if (s.type === 'tab') activeTabs[s.tabs] = s.tab
        else open = [...open.filter((a) => a !== s.name), s.name]
      }
      return { ...u, activeTabs, openAccordions: open }
    })
  }, [])

  const applyDirective = useCallback((d: UiDirective) => {
    reveal(d.reveal)
    setHighlight({ target: d.target, hint: d.hint, ts: Date.now(), also: d.also })
    window.setTimeout(() => {
      document.querySelector(`[data-name="${d.target}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 60)
  }, [reveal])

  useEffect(() => {
    if (!highlight) return
    const t = window.setTimeout(() => setHighlight(null), 7000)
    return () => window.clearTimeout(t)
  }, [highlight])

  // ------------------------------------------------------------ the chat: <agui-chat> + the formguide plugin
  const plugins = useMemo(() => [formguide({
    // the form as the backend last built it; pending typing is pushed first so the agent sees it
    getState: async (): Promise<FormState> => {
      window.clearTimeout(debounce.current)
      const cfg = await pushToJava({})
      const f = formRef.current!
      return { config: cfg, jsx_hash: f.hash, form_id: f.formId, ui: { ...uiRef.current, now: localNow() } }
    },
    // accepted card values go through the same path as user input: event -> form backend -> new config
    applyChanges: (changes) => pushToJava(changes),
    onDirective: (d) => applyDirective(d as UiDirective),
  })], [pushToJava, applyDirective])

  const onEvent = useCallback((e: { type: string; name?: string; value?: unknown }) => {
    if (e.type === 'CUSTOM' && e.name === 'agent_context') setAgentCtx(e.value as AgentCtx)
    if (e.type === 'CUSTOM' && e.name === 'run_stats') setRunStats(e.value as RunStats)
  }, [])

  const onThread = useCallback((id: string) => {
    const f = formRef.current
    if (f && id) { store.set(`formguide:thread:${f.formId}`, id); setThread(id) }
  }, [])
  useEffect(() => {
    const el = chatRef.current
    if (!el) return
    const f = (e: Event) => onThread((e as CustomEvent<string>).detail)
    el.addEventListener('agui:thread', f)
    return () => el.removeEventListener('agui:thread', f)
  }, [onThread, form])

  const prefill = () => {
    if (!form) return
    void chatRef.current?.run({
      notice: 'The form was prefilled from data the app already has.',
      forwardedProps: { prefill: { data: PROFILES[form.formId] ?? {}, language: navigator.language } },
    })
  }

  const ctxValue = useMemo(
    () => (config ? { config, ui, highlight, setValue, setTab, toggleAccordion, setFocused } : null),
    [config, ui, highlight, setValue, setTab, toggleAccordion, setFocused],
  )

  const header = (
    <div className="topbar">
      {HOSTED && <a className="back-docs" href="/">{'‹'} Docs</a>}
      <div className="seg" role="tablist">
        <button className={view === 'form' ? 'on' : ''} onClick={() => setView('form')}>Form + assistant</button>
        {!HOSTED && <button className={view === 'manager' ? 'on' : ''} onClick={() => setView('manager')}>Manager: documents</button>}
      </div>
      <Select className="ctl-field small" value={formId} onChange={(e) => setFormId(e.target.value)} aria-label="Demo form">
        {forms.map((f) => <option key={f} value={f}>{f}</option>)}
      </Select>
    </div>
  )

  if (view === 'manager') return <div className="page">{header}<Manager formId={formId} /></div>
  if (!form || !ctxValue || !thread) return <div className="page">{header}<div className="loading">Loading the form…</div></div>

  const jsxKb = (form.jsx.length / 1024).toFixed(0)
  const cfgKb = (JSON.stringify(config).length / 1024).toFixed(0)

  return (
    <div className="page">
    {header}
    <div className="app">
      <main className="form-pane">
        <header className="form-head">
          <h1>{form.title}</h1>
          <p className="muted">
            JSX {jsxKb} KB (once) · config {cfgKb} KB (every event)
            {agentCtx && <> · the agent sees ≈{agentCtx.stats.context_tokens.toLocaleString('en')} tokens instead of ≈{agentCtx.stats.config_tokens.toLocaleString('en')}</>}
          </p>
        </header>
        <FormProvider value={ctxValue}>
          <Render node={form.tree} />
        </FormProvider>
      </main>
      <aside className="chat-pane">
        <div className="chat-tools">
          <button className="link" onClick={() => setShowCtx((s) => !s)} disabled={!agentCtx}>
            {showCtx ? 'Hide' : 'What the agent sees'}
          </button>
          <button className="link" onClick={prefill} disabled={busy || !PROFILES[form.formId]}
            title="Start from data the app already has (AG-UI forwardedProps.prefill)">Prefill from profile</button>
          <Select className="ctl-field small" value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Chat language" title="Chat and dictation language">
            {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        </div>
        {showCtx && runStats && (
          <div className="ctx stats">
            last turn: first token {sec(runStats.ttft_ms)} · total {sec(runStats.total_ms)} · model {sec(runStats.model_ms)}
            {' '}· tools {sec(runStats.tool_ms)} ({runStats.tools.length}) · {runStats.tokens.input?.toLocaleString('en') ?? '-'} in /
            {' '}{runStats.tokens.output?.toLocaleString('en') ?? '-'} out
            {runStats.cache_hit_rate != null && <> · cache {Math.round(runStats.cache_hit_rate * 100)}%</>}
          </div>
        )}
        {showCtx && agentCtx && <pre className="ctx">{agentCtx.text}</pre>}
        <AguiChat
          ref={chatRef}
          className="chat-widget"
          url="/agent/run"
          mode="inline"
          threadId={thread}
          persistThread={false}
          lang={lang}
          title={form.title === form.formId ? "Form assistant" : form.title}
          subtitle="formguide · AI assistant, can make mistakes"
          plugins={plugins}
          tools={TOOLS}
          onEvent={onEvent}
          onRunStart={() => setBusy(true)}
          onRunEnd={() => setBusy(false)}
          onError={() => setBusy(false)}
        />
      </aside>
    </div>
    </div>
  )
}

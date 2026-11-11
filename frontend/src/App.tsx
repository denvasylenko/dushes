import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { HttpAgent } from '@ag-ui/client'
import { deleteThread, getThread, getThreadMessages, javaEvent, javaForm, javaForms, makeAgent, registerLayout, runTurn, uploadAttachment, type AgentEvent, type Attachment, type FormState, type TranscriptEntry, type Turn } from './api'
import { FormProvider, Render, type Highlight } from './Form'
import { parseJsx } from './jsx'
import Manager from './Manager'
import { SPEECH_LANGS, useSpeech } from './speech'
import type { Config, JsxNode, ProposedChange, RevealStep, UiDirective, UiState } from './types'

type ChatItem =
  | { kind: 'user'; text: string; files?: string[] }
  | { kind: 'assistant'; id: string; text: string }
  | { kind: 'tool'; name: string; input: unknown }
  | { kind: 'error'; text: string }
  | { kind: 'card'; id: string; changes: ProposedChange[]; status: 'pending' | 'accepted' | 'rejected' | 'dismissed' }
  | { kind: 'notice'; text: string }

type AgentCtx = { text: string; stats: { context_tokens: number; config_tokens: number } } | null

type LoadedForm = { formId: string; jsx: string; tree: JsxNode; hash: string; title: string }

const EMPTY_UI: UiState = { activeTabs: {}, openAccordions: [], focused: null }

/** Suggested first messages per demo form (users may write in any language). */
const SUGGESTIONS: Record<string, string[]> = {
  loan_application: ['Where do I start?', 'Where do I enter the department code?', 'I want a car loan of 1.5 million for 5 years'],
  barber_booking: ['Book me a haircut + beard next Tuesday around 3pm', 'How much is a haircut with Maria?', 'Book a kids haircut for my son, he is 6'],
}

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

function fromTranscript(entries: TranscriptEntry[]): ChatItem[] {
  return entries.map((e): ChatItem => {
    switch (e.kind) {
      case 'user':
        return { kind: 'user', text: e.text ?? '', files: e.files }
      case 'assistant':
        return { kind: 'assistant', id: e.id, text: e.text ?? '' }
      case 'tool':
        return { kind: 'tool', name: e.name ?? '', input: e.input }
      case 'card':
        return { kind: 'card', id: e.id, changes: (e.changes ?? []) as ProposedChange[], status: e.status ?? 'dismissed' }
      case 'notice':
        return { kind: 'notice', text: e.text ?? '' }
      default:
        return { kind: 'error', text: e.text ?? '' }
    }
  })
}

function localNow(): string {
  const d = new Date()
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  const date = d.toLocaleDateString('sv-SE') // YYYY-MM-DD
  const day = d.toLocaleDateString('en-US', { weekday: 'long' })
  return `${date} ${day} ${d.toTimeString().slice(0, 5)} (${tz})`
}

export default function App() {
  const [forms, setForms] = useState<string[]>([])
  const [formId, setFormId] = useState('loan_application')
  const [form, setForm] = useState<LoadedForm | null>(null)
  const [config, setConfig] = useState<Config | null>(null)
  const [ui, setUi] = useState<UiState>(EMPTY_UI)
  const [highlight, setHighlight] = useState<Highlight>(null)
  const [chat, setChat] = useState<ChatItem[]>([])
  const [busy, setBusy] = useState(false)
  const [agentCtx, setAgentCtx] = useState<AgentCtx>(null)
  const [showCtx, setShowCtx] = useState(false)
  const [thread, setThread] = useState('')
  const [view, setView] = useState<'form' | 'manager'>('form')

  const cfgRef = useRef<Config | null>(null)
  cfgRef.current = config
  const uiRef = useRef(ui)
  uiRef.current = ui
  const agentRef = useRef<HttpAgent | null>(null)
  const reqId = useRef(0)
  const debounce = useRef<number | undefined>(undefined)

  useEffect(() => {
    javaForms().then(setForms)
  }, [])

  // ------------------------------------------------------------ load: JSX once, config from the form backend
  useEffect(() => {
    setForm(null)
    javaForm(formId).then(async (f) => {
      // the frontend forwards the JSX (and the domain pack, if any) to the agent once
      const hash = await registerLayout(f.jsx, f.form_id, f.domain, f.config)
      const title = (f.domain?.title as string) ?? f.form_id
      // reopen: the same conversation, the saved form values and the sections that were open
      const threadId = store.get<string>(`formguide:thread:${f.form_id}`) ?? crypto.randomUUID()
      store.set(`formguide:thread:${f.form_id}`, threadId)
      const saved = store.get<Config['state']>(`formguide:state:${f.form_id}`)
      const cfg = saved ? await javaEvent(f.form_id, saved, {}) : f.config
      const [history, messages] = await Promise.all([getThread(threadId), getThreadMessages(threadId)])
      agentRef.current = makeAgent(threadId, messages)
      setForm({ formId: f.form_id, jsx: f.jsx, tree: parseJsx(f.jsx), hash, title })
      setConfig(cfg)
      setUi(store.get<UiState>(`formguide:ui:${f.form_id}`) ?? EMPTY_UI)
      setChat(fromTranscript(history.transcript))
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

  const newChat = async () => {
    if (!form || busy) return
    await deleteThread(thread)
    const id = crypto.randomUUID()
    store.set(`formguide:thread:${form.formId}`, id)
    agentRef.current = makeAgent(id)
    setThread(id)
    setChat([])
    setAgentCtx(null)
  }

  // ------------------------------------------------------------ form events -> form backend -> new config
  const pushToJava = useCallback(async (changes: Record<string, unknown>) => {
    const id = ++reqId.current
    const next = await javaEvent(formId, cfgRef.current!.state, changes)
    if (id === reqId.current) setConfig(next)
    return next
  }, [formId])

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
    setHighlight({ target: d.target, hint: d.hint, ts: Date.now() })
    window.setTimeout(() => {
      document.querySelector(`[data-name="${d.target}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 60)
  }, [reveal])

  useEffect(() => {
    if (!highlight) return
    const t = window.setTimeout(() => setHighlight(null), 7000)
    return () => window.clearTimeout(t)
  }, [highlight])

  // ------------------------------------------------------------ agent
  const onEvent = useCallback((e: AgentEvent) => {
    if (e.type === 'TEXT_MESSAGE_START') setChat((c) => [...c, { kind: 'assistant', id: e.messageId!, text: '' }])
    else if (e.type === 'TEXT_MESSAGE_CONTENT')
      setChat((c) => c.map((m) => (m.kind === 'assistant' && m.id === e.messageId ? { ...m, text: m.text + e.delta } : m)))
    else if (e.type === 'TOOL_CALL_DONE') setChat((c) => [...c, { kind: 'tool', name: e.name!, input: e.value }])
    else if (e.type === 'RUN_ERROR') setChat((c) => [...c, { kind: 'error', text: e.message ?? 'error' }])
    else if (e.type === 'CUSTOM') {
      if (e.name === 'ui_directive') applyDirective(e.value)
      else if (e.name === 'agent_context') setAgentCtx(e.value)
      else if (e.name === 'on_interrupt') {
        // ag-ui-langgraph convention: the value is a JSON string
        const v = typeof e.value === 'string' ? JSON.parse(e.value) : e.value
        setChat((c) => [...c, { kind: 'card', id: v.card_id ?? crypto.randomUUID(), changes: v.changes, status: 'pending' }])
      }
      else if (e.name === 'memory_compacted')
        setChat((c) => [...c, { kind: 'notice', text: 'Earlier messages were summarized for the assistant; the chat history is kept in full.' }])
    }
  }, [applyDirective])

  const baseState = (cfg: Config): FormState => ({
    config: cfg, jsx_hash: form!.hash, form_id: form!.formId, ui: { ...uiRef.current, now: localNow() },
  })

  const run = async (turn: Turn) => {
    setBusy(true)
    try {
      await runTurn(agentRef.current!, turn, onEvent)
    } finally {
      setBusy(false)
    }
  }

  const send = async (text: string, attachments: Attachment[] = []) => {
    if (!text.trim() || busy || !form) return
    window.clearTimeout(debounce.current)
    const fresh = await pushToJava({}) // the config sent to the agent must be up to date
    setChat((c) => [
      ...c.map((m) => (m.kind === 'card' && m.status === 'pending' ? { ...m, status: 'dismissed' as const } : m)),
      { kind: 'user', text, files: attachments.map((a) => a.filename) },
    ])
    await run({ message: text, state: { ...baseState(fresh), attachments } })
  }

  const prefill = async () => {
    if (busy || !form) return
    const fresh = await pushToJava({})
    setChat((c) => [...c, { kind: 'notice', text: 'The form was prefilled from data the app already has.' }])
    await run({ state: baseState(fresh), prefill: { data: PROFILES[form.formId] ?? {}, language: navigator.language } })
  }

  const answerCard = async (card: Extract<ChatItem, { kind: 'card' }>, accepted: boolean) => {
    setChat((c) => c.map((m) => (m.kind === 'card' && m.id === card.id ? { ...m, status: accepted ? 'accepted' : 'rejected' } : m)))
    setBusy(true)
    try {
      let cfg = cfgRef.current!
      if (accepted) {
        // applied through the same path as user input: event -> form backend -> new config
        cfg = await pushToJava(Object.fromEntries(card.changes.map((ch) => [ch.name, ch.value])))
        const last = card.changes[card.changes.length - 1]
        reveal(last.reveal)
        setHighlight({ target: last.name, hint: 'Filled in by the assistant', ts: Date.now() })
      }
      await runTurn(agentRef.current!, { state: baseState(cfg), resume: { accepted, config: cfg, ui: uiRef.current } }, onEvent)
    } finally {
      setBusy(false)
    }
  }

  const ctxValue = useMemo(
    () => (config ? { config, ui, highlight, setValue, setTab, toggleAccordion, setFocused } : null),
    [config, ui, highlight, setValue, setTab, toggleAccordion, setFocused],
  )

  const header = (
    <div className="topbar">
      <div className="seg" role="tablist">
        <button className={view === 'form' ? 'on' : ''} onClick={() => setView('form')}>Form + assistant</button>
        <button className={view === 'manager' ? 'on' : ''} onClick={() => setView('manager')}>Manager: documents</button>
      </div>
      <select value={formId} onChange={(e) => setFormId(e.target.value)} aria-label="Demo form">
        {forms.map((f) => <option key={f} value={f}>{f}</option>)}
      </select>
    </div>
  )

  if (view === 'manager') return <div className="page">{header}<Manager formId={formId} /></div>
  if (!form || !ctxValue) return <div className="page">{header}<div className="loading">Loading the form…</div></div>

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
        <div className="chat-head">
          <strong>Assistant</strong>
          <div className="row">
            <button className="link" onClick={() => setShowCtx((s) => !s)} disabled={!agentCtx}>
              {showCtx ? 'Hide' : 'What the agent sees'}
            </button>
            <button className="link" onClick={() => void prefill()} disabled={busy || !PROFILES[form.formId]}
              title="Start from data the app already has (AG-UI forwardedProps.prefill)">Prefill from profile</button>
            <button className="link" onClick={() => void newChat()} disabled={busy || !chat.length}>New chat</button>
          </div>
        </div>
        {showCtx && agentCtx && <pre className="ctx">{agentCtx.text}</pre>}
        <Chat items={chat} busy={busy} onSend={send} onCard={answerCard} thread={thread}
          suggestions={SUGGESTIONS[form.formId] ?? []} />
      </aside>
    </div>
    </div>
  )
}

function Chat({ items, busy, onSend, onCard, suggestions, thread }: {
  items: ChatItem[]
  busy: boolean
  onSend: (t: string, attachments?: Attachment[]) => void
  onCard: (c: Extract<ChatItem, { kind: 'card' }>, accepted: boolean) => void
  suggestions: string[]
  thread: string
}) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<Attachment[]>([])
  const [uploading, setUploading] = useState(false)
  const [fileErr, setFileErr] = useState('')
  const picker = useRef<HTMLInputElement>(null)
  // voice input: dictated text goes into the input box, appended to what was typed before
  const [speechLang, setSpeechLang] = useState(() => store.get<string>('formguide:speech-lang') ?? '')
  const before = useRef('')
  const speech = useSpeech(speechLang, (said) => setText((before.current ? before.current + ' ' : '') + said))
  const toggleMic = () => {
    if (speech.listening) return speech.stop()
    before.current = text.trim()
    speech.start()
  }

  const pick = async (list: FileList | null) => {
    if (!list?.length) return
    setUploading(true)
    setFileErr('')
    try {
      // uploaded to the agent service, scoped to this conversation; the agent reads it with a tool
      const added = await Promise.all(Array.from(list).map((f) => uploadAttachment(thread, f)))
      setFiles((x) => [...x, ...added])
    } catch (e) {
      setFileErr(String(e))
    } finally {
      setUploading(false)
      if (picker.current) picker.current.value = ''
    }
  }

  const submit = () => {
    const t = text.trim() || (files.length ? 'Please use the attached document.' : '')
    if (!t) return
    speech.cancel()   // the mic goes off and late results cannot bring the text back
    before.current = ''
    onSend(t, files)
    setText('')
    setFiles([])
  }

  // the message box grows with its text (up to a limit, then it scrolls)
  const box = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const el = box.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [text])
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [items])
  return (
    <>
      <div className="msgs">
        {items.length === 0 && (
          <div className="empty muted">
            Ask where to start, where a field is, or paste your details and the assistant will fill them in.
            {suggestions.map((s) => (
              <button key={s} className="chip" onClick={() => onSend(s)}>{s}</button>
            ))}
          </div>
        )}
        {items.map((m, i) => {
          switch (m.kind) {
            case 'user':
              return (
                <div key={i} className="msg user">
                  {m.files?.map((f) => <div key={f} className="file-chip">📎 {f}</div>)}
                  {m.text}
                </div>
              )
            case 'assistant':
              return <div key={i} className="msg bot">{m.text || '…'}</div>
            case 'error':
              return <div key={i} className="msg error">{m.text}</div>
            case 'notice':
              return <div key={i} className="notice muted">{m.text}</div>
            case 'tool':
              return <div key={i} className="tool">⚙ {m.name}({shortArgs(m.input)})</div>
            case 'card':
              return (
                <div key={i} className={`card ${m.status}`}>
                  <div className="card-title">Fill in these fields?</div>
                  <ul>
                    {m.changes.map((c) => (
                      <li key={c.name}><span className="muted">{c.label}:</span> <b>{c.display}</b></li>
                    ))}
                  </ul>
                  {m.status === 'pending' ? (
                    <div className="card-actions">
                      <button className="primary" disabled={busy} onClick={() => onCard(m, true)}>Fill in</button>
                      <button disabled={busy} onClick={() => onCard(m, false)}>Reject</button>
                    </div>
                  ) : (
                    <div className="muted">{{ accepted: 'Filled in', rejected: 'Rejected', dismissed: 'Skipped' }[m.status]}</div>
                  )}
                </div>
              )
          }
        })}
        {busy && <div className="typing muted">the assistant is thinking…</div>}
        <div ref={end} />
      </div>
      {speech.error && <div className="pending-files"><span className="err">{speech.error}</span></div>}
      {(files.length > 0 || fileErr) && (
        <div className="pending-files">
          {files.map((f) => (
            <span key={f.id} className="file-chip">
              📎 {f.filename}
              <button className="link" onClick={() => setFiles((x) => x.filter((y) => y.id !== f.id))} aria-label="Remove">×</button>
            </span>
          ))}
          {fileErr && <span className="err">{fileErr}</span>}
        </div>
      )}
      <form className="composer" onSubmit={(e) => { e.preventDefault(); submit() }}>
        <input ref={picker} type="file" hidden multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.txt,.md"
          onChange={(e) => void pick(e.target.files)} />
        <button type="button" title="Attach a document" disabled={busy || uploading} onClick={() => picker.current?.click()}>
          {uploading ? '…' : '📎'}
        </button>
        {speech.supported && (
          <>
            <button type="button" className={speech.listening ? 'mic on' : 'mic'} disabled={busy}
              title={speech.listening ? 'Stop dictation' : 'Dictate a message'} aria-pressed={speech.listening}
              onClick={toggleMic}>{speech.listening ? '■' : '🎤'}</button>
            <select className="mic-lang" value={speechLang} aria-label="Dictation language" disabled={speech.listening}
              onChange={(e) => { setSpeechLang(e.target.value); store.set('formguide:speech-lang', e.target.value) }}>
              {SPEECH_LANGS.map((l) => <option key={l} value={l}>{l ? l.slice(0, 2).toUpperCase() : 'Auto'}</option>)}
            </select>
          </>
        )}
        <textarea ref={box} rows={2} value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit() }
          }}
          placeholder={speech.listening ? 'Listening… speak, then press ■ or ➤' : 'Message the assistant… (Shift+Enter: new line)'}
          disabled={busy} />
        <button className="primary" disabled={busy || uploading || (!text.trim() && !files.length)}>➤</button>
      </form>
    </>
  )
}

function shortArgs(a: unknown): string {
  const s = JSON.stringify(a ?? {})
  return s.length > 70 ? s.slice(0, 70) + '…' : s
}

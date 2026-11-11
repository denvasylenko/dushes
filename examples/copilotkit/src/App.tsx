/**
 * formguide behind CopilotKit, with no CopilotKit runtime server: CopilotKit talks AG-UI
 * to the formguide endpoint directly through an HttpAgent.
 *
 * What the integration needs:
 * 1. register the form's JSX once (POST /agent/layouts) and keep the config your form backend returns;
 * 2. put {config, jsx_hash, form_id, ui} into the agent's state before each run;
 * 3. render cards with useInterrupt: field changes resolve with {accepted, config, names?},
 *    questions (type "ask") resolve with {answer: {ids?, text?}} or {accepted: false};
 * 4. (optional) frontend tools with useFrontendTool; prefill with forwardedProps.prefill.
 */
// CopilotKit re-exports the AG-UI HttpAgent it is built with (one copy of @ag-ui/client).
import { CopilotChat, CopilotKitProvider, HttpAgent, useAgent, useFrontendTool, useInterrupt } from '@copilotkit/react-core/v2'
import { useEffect, useMemo, useRef, useState } from 'react'
import { z } from 'zod'

type Config = { props: Record<string, Record<string, unknown>>; state: Record<string, unknown> }
type Change = { name: string; label: string; value: unknown; display: string }
type Card =
  | { type: 'set_fields'; card_id: string; changes: Change[] }
  | { type: 'ask'; card_id: string; question: string; options: { id: string; label: string }[]; multiple: boolean; allow_text: boolean }

const FORM_ID = 'barber_booking'

// Stand-in for your form backend: the demo server's mock (/java).
async function formBackendLoad() {
  return (await fetch(`/java/form?form_id=${FORM_ID}`)).json() as Promise<{ jsx: string; config: Config; domain: unknown }>
}
async function formBackendEvent(state: Config['state'], changes: Record<string, unknown>): Promise<Config> {
  const r = await fetch('/java/event', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ form_id: FORM_ID, state, changes }),
  })
  return r.json()
}

export default function App() {
  // One AG-UI agent pointing at formguide. CopilotKit marks direct agents as a development
  // option; in production put a CopilotRuntime in front of the same HttpAgent, or use selfManagedAgents.
  const agents = useMemo(() => ({ formguide: new HttpAgent({ url: '/agent/run' }) }), [])
  return (
    <CopilotKitProvider agents__unsafe_dev_only={agents} agentId="formguide">
      <Page />
    </CopilotKitProvider>
  )
}

function Page() {
  const { agent } = useAgent({ agentId: 'formguide' })
  const [hash, setHash] = useState('')
  const [config, setConfig] = useState<Config | null>(null)
  const cfgRef = useRef<Config | null>(null)
  cfgRef.current = config

  // 1. Load the form and register its JSX with the agent (once per JSX).
  useEffect(() => {
    formBackendLoad().then(async (f) => {
      const r = await fetch('/agent/layouts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsx: f.jsx, form_id: FORM_ID, domain: f.domain }),
      })
      setHash((await r.json()).jsx_hash)
      setConfig(f.config)
    })
  }, [])

  // 2. Every run carries the current form in the agent state.
  useEffect(() => {
    if (config && hash) agent.setState({ config, jsx_hash: hash, form_id: FORM_ID, ui: { now: new Date().toString() } })
  }, [agent, config, hash])

  // 3. Confirmation cards (formguide sends them as `on_interrupt`).
  useInterrupt({
    agentId: 'formguide',
    render: ({ event, resolve }) => {
      const card: Card = typeof event.value === 'string' ? JSON.parse(event.value) : (event.value as Card)
      if (card.type === 'ask') return <Ask card={card} onAnswer={(a) => void resolve(a)} />
      return <Changes card={card} onAnswer={async (names) => {
        // apply through the form backend so the config (visibility, options, errors) is recomputed;
        // names = the rows the user kept (null = rejected)
        const kept = names ? card.changes.filter((c) => names.includes(c.name)) : []
        const cfg = kept.length
          ? await formBackendEvent(cfgRef.current!.state, Object.fromEntries(kept.map((c) => [c.name, c.value])))
          : cfgRef.current!
        setConfig(cfg)
        agent.setState({ ...(agent.state as object), config: cfg })
        await resolve({ accepted: kept.length > 0, config: cfg, ...(names && kept.length < card.changes.length ? { names } : {}) })
      }} />
    },
  })

  // 4. A frontend tool: declared to the agent with each run, executed here.
  useFrontendTool({
    name: 'get_user_locale',
    description: "The user's browser language and time zone, for dates and times in local conventions.",
    parameters: z.object({}),
    handler: async () => ({ language: navigator.language, time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone }),
  })

  const prefill = () => agent.runAgent({ forwardedProps: { prefill: { data: { client_name: 'Anna Smith' } } } })

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(320px,420px)', height: '100vh' }}>
      <main style={{ padding: 16, overflow: 'auto', fontFamily: 'system-ui' }}>
        <h1 style={{ fontSize: 20 }}>Barber booking (values from the form backend)</h1>
        <button onClick={() => void prefill()} disabled={!hash}>Prefill from profile</button>
        <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
          {config ? JSON.stringify(config.state, null, 1) : 'Loading…'}
        </pre>
      </main>
      {hash ? <CopilotChat agentId="formguide" /> : <div style={{ padding: 16 }}>Loading the form…</div>}
    </div>
  )
}


function Changes({ card, onAnswer }: { card: Extract<Card, { type: 'set_fields' }>; onAnswer: (names: string[] | null) => void }) {
  const [keep, setKeep] = useState(() => card.changes.map((c) => c.name))
  return (
    <div className="card">
      <b>Fill in these fields?</b>
      <ul>{card.changes.map((c) => (
        <li key={c.name}>
          <label><input type="checkbox" checked={keep.includes(c.name)}
            onChange={() => setKeep((k) => (k.includes(c.name) ? k.filter((n) => n !== c.name) : [...k, c.name]))} />
          {' '}{c.label}: <b>{c.display}</b></label>
        </li>))}
      </ul>
      <button disabled={!keep.length} onClick={() => onAnswer(keep)}>Fill in</button> <button onClick={() => onAnswer(null)}>Reject</button>
    </div>
  )
}

function Ask({ card, onAnswer }: { card: Extract<Card, { type: 'ask' }>; onAnswer: (a: unknown) => void }) {
  const [picked, setPicked] = useState<string[]>([])
  const [text, setText] = useState('')
  return (
    <div className="card">
      <b>{card.question}</b>
      <div>{card.options.map((o) => card.multiple
        ? <label key={o.id}><input type="checkbox" checked={picked.includes(o.id)}
            onChange={() => setPicked((p) => (p.includes(o.id) ? p.filter((x) => x !== o.id) : [...p, o.id]))} /> {o.label} </label>
        : <button key={o.id} onClick={() => onAnswer({ answer: { ids: [o.id] } })}>{o.label}</button>)}
      </div>
      {card.allow_text && <input value={text} onChange={(e) => setText(e.target.value)} placeholder="or type your answer" />}
      <button disabled={!picked.length && !text.trim()}
        onClick={() => onAnswer({ answer: { ...(picked.length ? { ids: picked } : {}), ...(text.trim() ? { text: text.trim() } : {}) } })}>Send</button>
      {' '}<button onClick={() => onAnswer({ accepted: false })}>Skip</button>
    </div>
  )
}

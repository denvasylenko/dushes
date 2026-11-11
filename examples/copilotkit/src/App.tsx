/**
 * formguide behind CopilotKit, with no CopilotKit runtime server: CopilotKit talks AG-UI
 * to the formguide endpoint directly through an HttpAgent.
 *
 * What the integration needs:
 * 1. register the form's JSX once (POST /agent/layouts) and keep the config your form backend returns;
 * 2. put {config, jsx_hash, form_id, ui} into the agent's state before each run;
 * 3. render confirmation cards with useInterrupt and resolve them with {accepted, config};
 * 4. (optional) frontend tools with useFrontendTool; prefill with forwardedProps.prefill.
 */
// CopilotKit re-exports the AG-UI HttpAgent it is built with (one copy of @ag-ui/client).
import { CopilotChat, CopilotKitProvider, HttpAgent, useAgent, useFrontendTool, useInterrupt } from '@copilotkit/react-core/v2'
import { useEffect, useMemo, useRef, useState } from 'react'
import { z } from 'zod'

type Config = { props: Record<string, Record<string, unknown>>; state: Record<string, unknown> }
type Change = { name: string; label: string; value: unknown; display: string }
type Card = { type: string; card_id: string; changes: Change[] }

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
      const answer = async (accepted: boolean) => {
        // apply through the form backend so the config (visibility, options, errors) is recomputed
        const cfg = accepted
          ? await formBackendEvent(cfgRef.current!.state, Object.fromEntries(card.changes.map((c) => [c.name, c.value])))
          : cfgRef.current!
        setConfig(cfg)
        agent.setState({ ...(agent.state as object), config: cfg })
        await resolve({ accepted, config: cfg })
      }
      return (
        <div className="card">
          <b>Fill in these fields?</b>
          <ul>{card.changes.map((c) => <li key={c.name}>{c.label}: <b>{c.display}</b></li>)}</ul>
          <button onClick={() => void answer(true)}>Fill in</button> <button onClick={() => void answer(false)}>Reject</button>
        </div>
      )
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

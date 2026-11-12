---
title: CopilotKit
description: CopilotKit 1.86 talking AG-UI to formguide directly, with cards as interrupts and frontend tools.
---

formguide is a standard AG-UI agent, so CopilotKit connects through its own `HttpAgent` with no CopilotKit runtime server. The example in [`examples/copilotkit/`](https://github.com/denvasylenko/dushes/tree/main/examples/copilotkit) shows the four integration points.

## 1. One agent, pointing at formguide

```tsx
import { CopilotChat, CopilotKitProvider, HttpAgent, useAgent, useFrontendTool, useInterrupt } from '@copilotkit/react-core/v2'

const agents = useMemo(() => ({ formguide: new HttpAgent({ url: '/agent/run' }) }), [])
return (
  <CopilotKitProvider agents__unsafe_dev_only={agents} agentId="formguide">
    <Page />
  </CopilotKitProvider>
)
```

CopilotKit re-exports the `HttpAgent` it is built with, so there is one copy of `@ag-ui/client`.

## 2. Register the form, and send it with every run

```tsx
const r = await fetch('/agent/layouts', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ jsx, form_id: FORM_ID, domain }),
})
setHash((await r.json()).jsx_hash)

useEffect(() => {
  if (config && hash) agent.setState({ config, jsx_hash: hash, form_id: FORM_ID, ui: { now: new Date().toString() } })
}, [agent, config, hash])
```

## 3. Cards with `useInterrupt`

formguide sends a card as `CUSTOM on_interrupt` (a JSON string): `type: "set_fields"` for field changes, `type: "ask"` for a question.

```tsx
useInterrupt({
  agentId: 'formguide',
  render: ({ event, resolve }) => {
    const card = typeof event.value === 'string' ? JSON.parse(event.value) : event.value
    if (card.type === 'ask') return <Ask card={card} onAnswer={(a) => resolve(a)} />
    return <Changes card={card} onAnswer={async (names) => {
      if (!names) return resolve({ accepted: false })
      const config = await formBackendEvent(cfgRef.current.state, pick(card.changes, names))
      setConfig(config)
      resolve({ accepted: true, config, names })
    }} />
  },
})
```

| Card | Resolve with |
| --- | --- |
| field changes | `{accepted: true, config, names?}`, or `{accepted: false}` |
| question | `{answer: {ids: ["auto"]}}`, `{answer: {text}}`, or `{accepted: false}` |

Apply accepted values through your form backend, so visibility, options and errors are recomputed, then resume with the new config.

## 4. Frontend tools and prefill

Tools registered with `useFrontendTool` are sent with each run; when the model calls one, the run ends and its result comes back as a `tool` message. Prefill goes in `forwardedProps`:

```ts
agent.runAgent({ forwardedProps: { prefill: { data: profile } } })
```

## Run it

```bash
cd backend && ANTHROPIC_API_KEY=... uv run uvicorn demo.app:app --port 8000   # terminal 1
cd examples/copilotkit && npm install && npm run dev                           # terminal 2: http://localhost:5174
```

CopilotKit calls agents passed in `agents__unsafe_dev_only` a development option. For production, put a `CopilotRuntime` in front of the same `HttpAgent({url: "<formguide>/agent/run"})`, or use `selfManagedAgents` (CopilotKit's licensed tier). formguide's side does not change.

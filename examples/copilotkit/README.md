# formguide + CopilotKit

CopilotKit 1.86 talking AG-UI to formguide directly (`HttpAgent`), with no CopilotKit runtime server.
Shows the four integration points: registering the form, passing the form in the agent state,
confirmation cards with `useInterrupt`, a frontend tool with `useFrontendTool`, and prefill.

```bash
# terminal 1: the formguide demo server (agent + mock form backend)
cd backend && ANTHROPIC_API_KEY=... uv run uvicorn demo.app:app --port 8000
# terminal 2: this example
cd examples/copilotkit && npm install && npm run dev   # http://localhost:5174
```

CopilotKit calls agents passed in `agents__unsafe_dev_only` a development option. For production,
either put a `CopilotRuntime` in front of the same `HttpAgent({url: "<formguide>/agent/run"})`, or
use `selfManagedAgents` (CopilotKit's licensed tier). formguide's side does not change.

# formguide

A chat agent that guides users through large configurable forms: it shows where to click, explains fields, answers from the business's documents, reads user documents and fills fields with the user's confirmation. The core is form-agnostic and provider-agnostic; everything domain-specific is configured.

Documentation:
- [`docs/architecture.md`](docs/architecture.md) — how the parts fit together;
- [`docs/ui-components.md`](docs/ui-components.md) — start here if you build the form UI: what the form sends, what the agent sends back when it fills fields, and how each component must behave;
- [`docs/configuration.md`](docs/configuration.md) — models per provider and every YAML key;
- [`docs/observability.md`](docs/observability.md) — turn timings, tracing (LangSmith, Langfuse), speed tests and the live benchmark with its baseline;
- [`openspec/specs/`](openspec/specs) — behaviour contracts per capability, maintained with [OpenSpec](https://github.com/Fission-AI/OpenSpec) (`openspec list --specs`, `openspec validate --all --strict`);
- architecture pages with diagrams: https://denvasylenko.github.io/dushes/ — built from `docs/architecture-pages.html` plus the specs by `python3 scripts/build_docs_site.py`, deployed by `.github/workflows/docs.yml`.

## Quick start

```bash
pip install "formguide[all] @ git+https://github.com/denvasylenko/dushes.git#subdirectory=backend"
formguide init my-agent                            # formguide.yaml, a domain pack, a skill
formguide check --config my-agent/formguide.yaml   # loads it and reports; calls no model
ANTHROPIC_API_KEY=... formguide serve --config my-agent/formguide.yaml --cors "*"
```

The agent is now an AG-UI endpoint at `POST http://localhost:8000/agent/run`. The only required setting is the model: `model: "openai:gpt-5"` in the YAML, or `FORMGUIDE_MODEL=openai:gpt-5` with no file at all. Extras: `anthropic`, `openai`, `server`, `research`, `sqlite`, `all`; the core needs only LangGraph, LangChain core, Pydantic, PyYAML and pypdf. Or copy [`backend/formguide/`](backend/formguide) into your project.

## Connect a frontend (AG-UI first)

**The quickest way is the ready-made chat**, [`<agui-chat>`](docs/chat-widget.md): a Web Component (one `<script>` tag, npm, or a React wrapper) with the formguide plugin. It streams answers with a typewriter, shows the agent's steps, draws every card (field changes with edit and Undo, questions, file requests, confirmations), dictation, attachments and quick replies; every part is configurable.

```html
<agui-chat url="/agent/run"></agui-chat>
<script src="agui-chat.iife.js"></script>
<script>
  document.querySelector('agui-chat').use(AguiChat.formguide({ getState, applyChanges }))
</script>
```

Any AG-UI client works as is too. Each run carries the form in `state`; cards are interrupts; frontend tools and prefill use the protocol's own fields. See the [Integrate page](https://denvasylenko.github.io/dushes/#integrate) for the whole wire format.

```ts
import { HttpAgent } from "@ag-ui/client"           // or CopilotKit's re-export

const agent = new HttpAgent({ url: "/agent/run", threadId })
agent.setState({ config, jsx_hash, form_id })        // the form as your backend last built it
agent.addMessage({ id: crypto.randomUUID(), role: "user", content: "Where do I start?" })
await agent.runAgent({ tools: frontendTools }, {
  onCustomEvent: ({ event }) => event.name === "on_interrupt" && showCard(JSON.parse(event.value)),
})
// on_interrupt has a `type`: "set_fields" (a field-change card) or "ask" (a question card with options)
// answer a card: agent.runAgent({ forwardedProps: { command: { resume: { accepted, config, names? } } } })
// answer a question:            ... resume: { answer: { ids: ["auto"] } }  or  { answer: { text } }  or  { accepted: false }
// prefill:       agent.runAgent({ forwardedProps: { prefill: { data: profile } } })
```

- **CopilotKit 1.86**: [`examples/copilotkit/`](examples/copilotkit) — `CopilotKitProvider` with an `HttpAgent` (no CopilotKit runtime server), cards with `useInterrupt`, a frontend tool with `useFrontendTool`, prefill.
- **`<agui-chat>`**: the demo UI ([`frontend/src/App.tsx`](frontend/src/App.tsx), React wrapper) and a plain-HTML page with live settings ([`examples/widget-html/`](examples/widget-html), served at http://localhost:8000/examples/widget/).
- **Cards**: field-change cards (a checkbox per row; `names` keeps a subset) and question cards (`ask_user`: options from the model or from a field, single or multiple choice, typed answers); payloads in [docs/ui-components.md](docs/ui-components.md#25-which-one-the-question-card). `interrupt_mode: legacy` (default; `CUSTOM on_interrupt`, what CopilotKit reads), `structured` (AG-UI 1.0 `RUN_FINISHED.outcome` + `resume[]`) or `both`.
- **Restore a chat**: `GET /agent/threads/{id}?format=agui` returns AG-UI messages for `setMessages`.

## Use it from Python

```python
from formguide.app import create_app
app = create_app("formguide.yaml", cors=["https://my.app"])        # a whole FastAPI app

from formguide import FormGuide, load_config                     # or inside your own FastAPI app
from formguide.server import create_router
guide = FormGuide(load_config("formguide.yaml"))
app.include_router(create_router(guide), prefix="/agent")
```

Without a web framework, call the guide directly:

```python
info = guide.register_form(jsx, form_id="loan_application", domain=optional_pack)   # once per JSX
state = {"config": config, "jsx_hash": info["jsx_hash"], "form_id": "loan_application", "ui": ui}
async for event in guide.run(thread_id, message="Where do I enter my tax id?", state=state):
    ...   # AG-UI events as dicts: TEXT_MESSAGE_*, TOOL_CALL_*, CUSTOM ui_directive / on_interrupt, RUN_FINISHED
async for event in guide.run(thread_id, resume={"accepted": True, "config": new_config}):
    ...   # after the user answered a confirmation card
await guide.suggest_prefill(state, data=profile)    # values to prefill, without a chat
```

## Configure

Everything can be set in code (`GuideConfig`) or YAML (`load_config`). The full reference — how to write a model for each provider, which role falls back to which, every key with its default — is [`docs/configuration.md`](docs/configuration.md); a working file is [`demo/formguide.yaml`](backend/demo/formguide.yaml).

| What | Options |
|---|---|
| Models (per role: agent, research, compile, extract, memory) | `model: "openai:gpt-5"` for all roles; or per role: any LangChain `BaseChatModel`, `"provider:model"` strings, `{provider, model, ...}`, `{class: "langchain_openai:AzureChatOpenAI", ...}` |
| Component library | `components:` JSX tag → role, or a field spec saying how the component stores its value (id or option object, `"Y"`/`"N"`, `"31.05.1990"`, your own codec); see [docs/ui-components.md](docs/ui-components.md#15-your-components-store-values-differently-describe-them) |
| Domain packs | shipped with the form › `provider` callable › `packs` dict › JSON dir › neutral default |
| Business documents | `KnowledgeBase(root, index=BM25Index() \| VectorStoreIndex(any LangChain VectorStore), scopes={form: [namespaces]})` |
| Skills | folders with `SKILL.md` (name, description, forms, tools) or `Skill(...)` in code |
| Extra tools | any LangChain `BaseTool`; frontend tools come from the client per run |
| History | model history: any LangGraph checkpointer (in memory by default; `sqlite_checkpointer(path)`, Postgres, Redis); display transcript: any `TranscriptStore` (files by default) |
| Long chats | `MemoryConfig(max_history_tokens, keep_turns, model)` |
| Cards | `interrupt_mode`: `legacy` · `structured` · `both` |

Model requirements: tool calling (agent, research), structured output (compile, extract, prefill from text), vision / PDF input (extracting from scans).

Card and prefill values are written in the form's own format. Since component value formats were added, a number goes out as a JSON number (`250000`) by default; set `value: string` on the number component to keep `"250000"`.

## Layout

```
backend/
  formguide/        the library — guide.py · agui.py · server.py · app.py · cli.py · prefill.py · agent/ · form/ · knowledge/
  demo/             an example integration: mock form backend, FastAPI app, YAML config, skills, samples
  tests/            offline tests (scripted model, no API keys)
  scripts/          chat_harness.py: live conversations with the running demo
packages/agui-chat/ the chat widget: <agui-chat> Web Component, formguide plugin, React wrapper (npm run build / test)
frontend/           demo UI (React) using the widget; the library does not need it
examples/copilotkit CopilotKit 1.86 client
examples/widget-html the widget from one script tag, with a live settings panel
```

## Run the demo

```bash
cd packages/agui-chat && npm install && npm run build && cd ../..   # the chat widget (also for /examples/widget/)
cd frontend && npm install && npm run build && cd ..
cd backend && ANTHROPIC_API_KEY=... uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo
```

Open http://localhost:8000. Two demo forms with nothing in common: `loan_application` (221 fields, 8 tabs, nested up to 4 levels) and `barber_booking` (a 4-step wizard). "Manager: documents" uploads business documents for a form (`demo/samples/kb/` has examples); 📎 in the chat attaches a user document (`demo/samples/attachments/`). 🎤 dictates a message through the browser's speech recognition (Chrome, Edge, Safari; the language select above the chat sets the chat's language and dictation, Auto = the browser's; Chrome sends the audio to its own speech service). The chat is [`<agui-chat>`](docs/chat-widget.md); http://localhost:8000/examples/widget/ shows it from one script tag with a panel that switches every option live.

Note: `--reload` watches `.py` files only; after editing `formguide.yaml`, touch a `.py` file or restart.

## Test

```bash
cd backend && uv run pytest -q                                          # offline
cd backend && uv run python scripts/chat_harness.py                     # live, needs the demo server with a key
cd backend && uv run python scripts/chat_harness.py --form barber_booking
cd packages/agui-chat && npm test                                    # the chat widget (Vitest)
cd backend && uv run python scripts/bench.py --repeat 3                 # live speed benchmark (see docs/observability.md)
```

## How it works (short)

- **Context.** Each message brings the fresh config. The model sees a collapsed outline, the open section and what changed since the last message: ~1K tokens instead of ~16K of raw config. Details come through tools.
- **Protocol.** Strict AG-UI: input validated as `RunAgentInput`, every event validated and encoded with the official package; server tools stream as tool calls with results; frontend tools end the run and their results come back as `tool` messages.
- **Prefill.** Known data is validated against the form (field names directly, anything else through extraction); the agent proposes what is editable now and keeps the rest for locked steps.
- **Changes.** The agent never writes the config. `propose_changes` validates (visible, enabled, not read-only, value in options) and interrupts; the frontend shows a card, applies the change through the form backend and resumes with the new config.
- **Dependencies.** Inferred from config diffs (the config does not declare them) and persisted per form.
- **Business documents.** Compiled once into rules and field notes in the domain pack; a deep-agent researcher (`deepagents`, read-only `/docs/` filesystem + ranked search) handles the long tail and returns a cited answer.
- **User documents.** Read by a separate extraction call; only the values (with confidence and evidence) enter the conversation.
- **Long chats.** Older turns are compacted into a conversation memory by a cheap model (goal, values not yet in the form, decisions, rejections, next step); the form state is never summarized because it is rebuilt from the config every turn.
- **Chat history.** The conversation the user sees is a separate display transcript: compaction never touches it, and with durable stores it survives reloads and restarts (`GET /threads/{id}` restores it, including a pending card).
- **Append-only history.** The system prompt is frozen per thread; knowledge updates arrive as `<updated_instructions>` in a new message. Models that bind reasoning to the exact prefix (Claude Opus 5.5) otherwise reject earlier reasoning blocks; if a provider still rejects them, the turn is retried once without them.

## Next steps

- Auth on the knowledge-base endpoints (anyone can upload or delete documents today).
- Embeddings for field search (`form/search.py`) like the knowledge index already supports.
- PII tokenization for chat text and attachments in strict regimes.
- Run the live harness against OpenAI / Azure (only offline payload checks so far).

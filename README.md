# formguide

A chat agent that guides users through large configurable forms: it shows where to click, explains fields, answers from the business's documents, reads user documents and fills fields with the user's confirmation. The core is form-agnostic and provider-agnostic; everything domain-specific is configured.

Documentation:
- [`docs/architecture.md`](docs/architecture.md) — how the parts fit together;
- [`openspec/specs/`](openspec/specs) — behaviour contracts per capability, maintained with [OpenSpec](https://github.com/Fission-AI/OpenSpec) (`openspec list --specs`, `openspec validate --all --strict`);
- architecture pages with diagrams: https://denvasylenko.github.io/dushes/ — built from `docs/architecture-pages.html` plus the specs by `python3 scripts/build_docs_site.py`, deployed by `.github/workflows/docs.yml`.

## Layout

```
backend/
  formguide/        the library: install it (pip install -e backend) or copy the folder
  demo/             an example integration: mock form backend, FastAPI app, YAML config, skills, samples
  tests/            offline tests (scripted model, no API keys)
  scripts/          chat_harness.py: live conversations with the running demo
frontend/           optional demo UI (React); the library does not need it
```

## Use it

```python
from formguide import FormGuide, load_config
from formguide.server import create_router          # optional FastAPI router

guide = FormGuide(load_config("formguide.yaml"))
app.include_router(create_router(guide), prefix="/agent")
```

Without FastAPI, call the guide directly:

```python
info = guide.register_form(jsx, form_id="loan_application", domain=optional_pack)   # once per JSX
state = {"config": config, "jsx_hash": info["jsx_hash"], "form_id": "loan_application", "ui": ui}
async for event in guide.run(thread_id, message="Where do I enter my tax id?", state=state):
    ...   # AG-UI events: TEXT_MESSAGE_*, CUSTOM ui_directive / on_interrupt / tool_activity / memory_compacted
async for event in guide.run(thread_id, resume={"accepted": True, "config": new_config}):
    ...   # after the user answered a confirmation card
```

## Configure

Everything can be set in code (`GuideConfig`) or YAML (`load_config`); see `formguide/config.py` and `demo/formguide.yaml`.

| What | Options |
|---|---|
| Models (per role: agent, research, compile, extract, memory) | any LangChain `BaseChatModel`; `"openai:gpt-5"` strings; `{provider, model, ...}`; `{class: "langchain_openai:AzureChatOpenAI", ...}` |
| Component library | `ComponentMap`: JSX tag → role |
| Domain packs | shipped with the form › `provider` callable › `packs` dict › JSON dir › neutral default |
| Business documents | `KnowledgeBase(root, index=BM25Index() \| VectorStoreIndex(any LangChain VectorStore), scopes={form: [namespaces]})` |
| Skills | folders with `SKILL.md` (name, description, forms, tools) or `Skill(...)` in code |
| Extra tools | any LangChain `BaseTool` |
| History | model history: any LangGraph checkpointer (in memory by default; `sqlite_checkpointer(path)`, Postgres, Redis); display transcript: any `TranscriptStore` (files by default) |
| Long chats | `MemoryConfig(max_history_tokens, keep_turns, model)` |

Model requirements: tool calling (agent, research), structured output (compile, extract), vision / PDF input (extracting from scans). Install the provider's LangChain package (`langchain-anthropic` is included; `pip install -e "backend[openai]"` for OpenAI / Azure).

## Run the demo

```bash
cd frontend && npm install && npm run build && cd ..
cd backend && ANTHROPIC_API_KEY=... uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo
```

Open http://localhost:8000. Two demo forms with nothing in common: `loan_application` (221 fields, 8 tabs, nested up to 4 levels) and `barber_booking` (a 4-step wizard). "Manager: documents" uploads business documents for a form (`demo/samples/kb/` has examples); 📎 in the chat attaches a user document (`demo/samples/attachments/`).

Note: `--reload` watches `.py` files only; after editing `formguide.yaml`, touch a `.py` file or restart.

## Test

```bash
cd backend && uv run pytest -q                                          # offline
cd backend && uv run python scripts/chat_harness.py                     # live, needs the demo server with a key
cd backend && uv run python scripts/chat_harness.py --form barber_booking
```

## How it works (short)

- **Context.** Each message brings the fresh config. The model sees a collapsed outline, the open section and what changed since the last message: ~1K tokens instead of ~16K of raw config. Details come through tools.
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

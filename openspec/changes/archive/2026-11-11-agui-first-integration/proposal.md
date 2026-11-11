# Proposal

## Why

formguide should drop into any app that speaks AG-UI (CopilotKit or any other AG-UI client), not only into our demo. Today the events are AG-UI-shaped but not guaranteed to follow the protocol (errors are followed by `RUN_FINISHED`, tool activity uses a custom event, interrupts use our own JSON object), frontend tools that AG-UI clients declare are ignored, and setting the project up means copying the demo. Teams also want the form prefilled from data they already have (a CRM profile, a previous application, a document) before the user types anything.

## What Changes

- **AG-UI first.** The router validates `RunAgentInput` and encodes events with the official `ag-ui-protocol` package (SSE or protobuf by `Accept`). Server tools are streamed as `TOOL_CALL_START/ARGS/END` + `TOOL_CALL_RESULT`; a run that fails ends with `RUN_ERROR` only. Confirmation cards are AG-UI interrupts: the legacy CopilotKit channel (`CUSTOM on_interrupt` with a JSON string) by default, the AG-UI 1.0 structured outcome (`RUN_FINISHED.outcome.interrupts`) when enabled; resume via `RunAgentInput.resume[]` or `forwardedProps.command.resume`.
- **Frontend tools.** Tools the client declares in `RunAgentInput.tools` (for example CopilotKit `useFrontendTool` / `useCopilotAction`) are offered to the model; calls are streamed to the client, the run ends, and the next run's `tool` messages feed the results back.
- **Restore for AG-UI clients.** `GET /threads/{id}?format=agui` returns the transcript as AG-UI messages, ready for `agent.setMessages`.
- **Prefill.** `FormGuide.suggest_prefill()` maps known data, text or attachments to validated field values without a chat; a run with `forwardedProps.prefill` lets the agent propose them in a confirmation card and carry locked steps forward.
- **Quick start.** `formguide.app.create_app(config)` returns a ready FastAPI app; a `formguide` CLI with `init` (starter config), `check` (validate config without calling a model) and `serve`. Packaging with optional extras: `anthropic`, `openai`, `server`, `research`, `sqlite`, `all`.
- **Examples.** The demo frontend uses the official `@ag-ui/client`; a CopilotKit example shows the integration.

## Capabilities

### New Capabilities
- `agui-protocol`: the AG-UI contract: input, events, interrupts and resume, frontend tools, errors.
- `form-prefill`: filling a form from data the host app already has.
- `quick-start`: packaging, `create_app`, the CLI.

### Modified Capabilities
- `http-api`: AG-UI validation and encoding, AG-UI message export, prefill endpoint.

## Impact

- `formguide/server.py`, `guide.py`, `agent/graph.py`, `agent/tools.py`, new `formguide/agui.py`, `formguide/prefill.py`, `formguide/app.py`, `formguide/cli.py`; `pyproject.toml` (extras, console script, build system).
- Demo frontend switches to `@ag-ui/client`; new `examples/copilotkit/`.
- Docs: integration page, links to the source on GitHub.

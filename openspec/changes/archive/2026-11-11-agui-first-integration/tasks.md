# Tasks

## 1. AG-UI
- [x] 1.1 Router: validate `RunAgentInput`, encode with `ag_ui` `EventEncoder`
- [x] 1.2 Server tools as `TOOL_CALL_*` + `TOOL_CALL_RESULT`; `RUN_ERROR` is terminal
- [x] 1.3 Interrupt channels (legacy / structured / both) and resume via `resume[]` or `forwardedProps.command.resume`
- [x] 1.4 Frontend tools from `RunAgentInput.tools`: bind, stream calls, end turn, feed results back
- [x] 1.5 `GET /threads/{id}?format=agui`

## 2. Prefill
- [x] 2.1 `FormGuide.suggest_prefill()` and `POST /prefill`
- [x] 2.2 Chat prefill via `forwardedProps.prefill`

## 3. Quick start
- [x] 3.1 `formguide.app.create_app`, `formguide` CLI (`init`, `check`, `serve`)
- [x] 3.2 Packaging: extras, console script, lazy optional imports; `uv build` works

## 4. Clients and docs
- [x] 4.1 Demo frontend on `@ag-ui/client`
- [x] 4.2 `examples/copilotkit/` and a browser check
- [x] 4.3 Docs: integration page, GitHub links, layout check on desktop and phone
- [x] 4.4 Tests (AG-UI event order with the official verifier rules, frontend tools, prefill, CLI), live regression

# Tasks

## 1. Server

- [ ] 1.1 Parse `proactive:` with defaults; verify config tests
- [ ] 1.2 Treat a run with `moment` as a moment: one suggestion or nothing, no history, no transcript, limits per page and per dismissed target; verify with tests for each kind, the limits and "off by default"
- [ ] 1.3 Document in `backend/configuration.mdx` and `reference/configuration.md`; build passes

## 2. Widget

- [ ] 2.1 Agree with the UX/UI session, then detect `idle_field`, `form_error` and `leaving` behind `proactive`, never while typing or running; verify with widget tests and in the browser
- [ ] 2.2 Document the attribute in `reference/agui-chat.md` and `frontend/chat-widget.mdx`; build passes

## 3. Checks

- [ ] 3.1 `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q`, `cd site && npm run build` pass

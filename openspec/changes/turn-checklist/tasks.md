# Tasks

## 1. Server

- [ ] 1.1 Add `show_plan` to the form agent and Dushes, emit and advance `plan` per round, on the answer and on failure; verify with scripted-model tests for each state change and a second call being ignored
- [ ] 1.2 Add the prompt rule; verify the "simple question" scenario emits no plan
- [ ] 1.3 Record the finished plan in the transcript; verify a restore returns it
- [ ] 1.4 Document the event in `reference/agui-events.md` and `concepts/turn.mdx`; build passes

## 2. Widget

- [ ] 2.1 Agree with the UX/UI session, then draw the checklist in place of the dots and keep it above the answer; verify with widget tests and in the browser at 390 px and desktop, light and dark
- [ ] 2.2 Add a card-gallery specimen and update the landing demo script if it shows a long turn; build passes

## 3. Checks

- [ ] 3.1 `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q`, `cd site && npm run build` pass

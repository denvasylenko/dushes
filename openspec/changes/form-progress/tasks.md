# Tasks

## 1. Progress

- [ ] 1.1 Emit `progress` at the end of each form turn from the form context's counts; verify with a scripted-model test in `backend/tests/`
- [ ] 1.2 Show the header line in `<agui-chat>` (agree with the UX/UI session first); verify with a widget test and in the browser at 390 px and desktop, light and dark
- [ ] 1.3 Document the event in `reference/agui-events.md` and `frontend/chat-widget.mdx`; build passes

## 2. Drafts

- [ ] 2.1 Keep draft pointers per site thread and form, drop them on submit or a host report; return `drafts` from `GET /site/threads/{id}`; verify with tests in `test_site.py`
- [ ] 2.2 Add `Dushes(drafts=fn)`; verify the host list wins in a test
- [ ] 2.3 Give Dushes the drafts and the once-per-page continue suggestion; verify the "Back from the FAQ" scenario with a scripted model
- [ ] 2.4 Update `backend/dushes.mdx` ("Every option"), `frontend/dushes.mdx` and `reference/http-api.md`; build passes

## 3. Checks

- [ ] 3.1 Try it in the demo (fill part of the loan form, go to FAQ, come back through the chat); `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q`, `cd site && npm run build` pass

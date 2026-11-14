# Tasks

## 1. Recording

- [ ] 1.1 Record kept rows and applied answers at the confirm node with source and time, stored next to the transcript; verify with scripted-model tests for full, partial and rejected cards and a restart
- [ ] 1.2 Add `GET /threads/{id}/changes?form_id=`; verify with an HTTP test; document in `reference/http-api.md`

## 2. Asking and undoing

- [ ] 2.1 Add `list_changes` and the prompt rule; verify the "Asking later" scenario with a scripted model
- [ ] 2.2 Undo through `propose_changes` with previous values and dependent fields; verify the "Put the old amount back" scenario and an invalid previous value
- [ ] 2.3 Document in `concepts/turn.mdx` and `frontend/cards.mdx`; build passes

## 3. Checks

- [ ] 3.1 `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q`, `cd site && npm run build` pass

# Tasks

## 1. Undo

- [ ] 1.1 Add `undo` to `SiteTool`, emit `receipt {text, undo_id}`, store ids for one hour; verify with tests in `test_site.py`
- [ ] 1.2 Add `POST /site/undo/{undo_id}` (once, then 404); verify with HTTP tests

## 2. Cards and held tools

- [ ] 2.1 Accept `{text, card}` from host tools and show the blocks card; verify with a scripted-model test and in the demo
- [ ] 2.2 Hold `confirm=True` tools behind a confirmation card and resume on the answer; verify accepted and rejected cases
- [ ] 2.3 Add the action rule to Dushes' prompt; verify the failing-action scenario

## 3. Demo and docs

- [ ] 3.1 Add a reversible and a card-returning host tool to `backend/demo/site_app.py`; check in the browser at 390 px and desktop
- [ ] 3.2 Update `backend/dushes.mdx` (host tools, "Every option") and `reference/agui-events.md`; build passes
- [ ] 3.3 `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q` pass

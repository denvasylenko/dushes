# Tasks

## 1. Page context on the server

- [ ] 1.1 Normalise `state.page.content` and `state.page.snapshot` into sections (id, title, text, table) with the mode rule (`host`, `snapshot`, `both`, `off`); verify with unit tests in `backend/tests/test_page_context.py` for each mode
- [ ] 1.2 Render `<page_context>` into Dushes' current message, visible section first, cut to `max_chars` with a cut mark; verify with a scripted-model test that reads the model's last message
- [ ] 1.3 Read `page_context:` from the site map and `Dushes(page_context=...)`; verify with a test that the argument overrides the map
- [ ] 1.4 Add the page-is-data rule to Dushes' prompt; verify with the injected-line scenario test
- [ ] 1.5 Update `backend/dushes.mdx` (page config, modes, "Every option") and `concepts/architecture.md`; `cd site && npm run build` passes

## 2. Highlight

- [ ] 2.1 Add the `highlight` tool, validated against this run's page ids and the current page's site-map sections, emitting `site_directive {type: "highlight", ...}`; verify with tests for a valid id and an invented one
- [ ] 2.2 Handle the highlight directive in `frontend/src/site/Site.tsx` (scroll and ring) and send page content from one demo page; verify in the browser at 390 px and desktop
- [ ] 2.3 Document the directive type in `form/contract.mdx`, `reference/agui-events.md` and `frontend/dushes.mdx`; build passes

## 3. The widget's snapshot

- [ ] 3.1 Agree the change with the UX/UI session (it owns `packages/agui-chat`) before editing
- [ ] 3.2 Add `page-snapshot`, `page-snapshot-skip` and `page-snapshot-max` to `<agui-chat>`, collecting the snapshot as specified when `state.page.content` is absent; verify with widget tests for tables, skipped controls and `data-agui-skip`, and the size limit
- [ ] 3.3 Document the attributes in `reference/agui-chat.md` and `frontend/dushes.mdx`; build passes

## 4. Checks

- [ ] 4.1 `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q` and `cd site && npm run build` all pass

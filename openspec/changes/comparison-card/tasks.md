# Tasks

## 1. Dushes asks

- [ ] 1.1 Add `ask_user` to Dushes with a pending question in the site thread and resume on the answer; verify with tests in `test_site.py` and a reload restoring the open question

## 2. The card

- [ ] 2.1 Add `show_comparison` with validation (counts, one recommended with a reason, actions checked against the site map) and the `comparison` event; verify with unit tests
- [ ] 2.2 Carry out a tapped action (`open_form` / `navigate`); verify the "Apply for the recommended one" scenario with a scripted model
- [ ] 2.3 Add the advisor skill to the demo; verify with a scripted conversation

## 3. Widget and docs

- [ ] 3.1 Agree with the UX/UI session, then render the card (columns, swipe on a phone, recommended first); verify in the browser at 390 px and desktop, light and dark, and add a card-gallery specimen
- [ ] 3.2 Document in `frontend/cards.mdx`, `backend/dushes.mdx` and `reference/agui-events.md`; build passes
- [ ] 3.3 `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q` pass

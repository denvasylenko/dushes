# Tasks

## 1. Question tool and pending slot

- [x] 1.1 `agent/tools.py`: an `ask_user` tool schema and handler:
  - options normalised to `[{id, label}]`, and `field` options from the overlay;
  - limits of 12 options and 300 characters;
  - `ToolCtx.pending_question`;
  - both waiting tools refuse when either one is pending.
- [x] 1.2 `agent/graph.py`:
  - the `tools` node stores `pending.kind`;
  - frontend tools are skipped next to `ask_user` too;
  - `route_tools` is unchanged.
- [x] 1.3 New `agent/interaction.py`: `read_answer(question, resume)` and `read_decision(changes, resume)`, shared by the graph and the transcript.
- [x] 1.4 `agent/graph.py` `confirm`:
  - the `ask` branch sends the answer text as the tool result;
  - `set_fields` with `names` builds the applied/declined text and uses the kept names for the diff.
- [x] 1.5 `agent/graph.py` `sync`: the ignored-item text covers questions.
- [x] 1.6 `agent/prompts.py`: the question rule (choices and ambiguity only, never for confirmation, do not repeat).

## 2. Transport and transcript

- [x] 2.1 `guide.py`:
  - `question` transcript entries;
  - the structured outcome reason `ask_user` with metadata;
  - resume status `answered` / `dismissed` / `partial` with names;
  - the docstring.
- [x] 2.2 `transcript.py`: the docstring and `pending_card` returning a pending card or question.
- [x] 2.3 `agui.py`: `_resume_value` turns a non-JSON string into `{answer: {text}}`, and `confirm` still reads yes/ok text on a field-change card as accepted.

## 3. Clients

- [x] 3.1 `frontend/src/types.ts` and `App.tsx`:
  - a question card (single, multiple, free text);
  - field-change card rows with checkboxes, sending only the kept changes and `names`;
  - both restored after a reload.
- [x] 3.2 `examples/copilotkit/src/App.tsx`: render both kinds in `useInterrupt`, then build both frontends.

## 4. Tests

- [x] 4.1 New `tests/test_questions.py`:
  - own options;
  - field options, including a multiselect defaulting to multiple;
  - the subset, too-many-options and non-choice refusals;
  - answers by ids, text and string;
  - invalid ids and `cancelled` counting as skipped;
  - two waiting calls in one response;
  - an ignored question;
  - structured outcome reason and metadata;
  - transcript statuses and `pending_card` kind after a reload.
- [x] 4.2 Partial acceptance tests:
  - names subset text and diff;
  - empty names counting as rejection;
  - unknown names ignored;
  - transcript `partial`.
- [x] 4.3 `backend/scripts/chat_harness.py`:
  - a scenario where an ambiguous request yields a question card;
  - a scenario where "my name is Anna" does not.
- [x] 4.4 Run `uv run pytest -q`.

## 5. Docs and specs

- [x] 5.1 `docs/ui-components.md`: the question card payload, answering it, partial acceptance, checklist and troubleshooting rows.
- [x] 5.2 `docs/architecture.md` (the wire section and the turn) and `README.md` (the client snippet notes `type`).
- [x] 5.3 `docs/architecture-pages.html`: the Build the UI and Integrate pages. Run `python3 scripts/build_docs_site.py`, then republish the artifact.
- [x] 5.4 Run `openspec validate --all --strict`, `python3 scripts/check_english.py` and the tests.

## Workflow follow-up

- Archive the change with `/opsx:archive` after it is implemented and verified.

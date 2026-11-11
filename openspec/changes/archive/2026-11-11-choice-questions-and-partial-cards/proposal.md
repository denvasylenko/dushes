# Proposal

## Why

The only interactive element the agent can send today is the field-change card, and it can only be accepted or rejected as a whole. When the agent needs a decision ("which loan type?", "is the actual address the same as registration?") it asks in plain text. The user then types an answer that the agent has to interpret, which costs a turn and invites mistakes. Users also cannot keep three good suggestions out of four: they must reject the whole card and explain in text.

## What Changes

- **Question cards.** A new tool `ask_user` lets the model ask one question with clickable options and pause the turn, like a field-change card. It works in three ways:
  - options given by the model;
  - options taken from a field's current choices, with `field: <name>`;
  - free text only.

  Single or multiple choice is supported, and a free-text answer is allowed unless turned off. The client receives a second interrupt type, `{type: "ask", card_id, question, options, multiple, allow_text, field?}`, through the same channels as cards: legacy `CUSTOM on_interrupt`, or structured `RUN_FINISHED.outcome` with reason `ask_user`. The client answers by resuming with `{answer: {ids?, text?}}`. Cancelling skips the question. The model gets the answer as the tool result and continues the same turn.
- **Partial acceptance of field-change cards.** A resume may carry `{accepted: true, names: [...], config}` to apply only some of the proposed changes. The model is told which changes were applied and which were declined. The transcript records the card as `partial` with the applied names.
- **One waiting interaction per step.** The agent still sends at most one card or question per step. A second `propose_changes` or `ask_user` in the same response is refused, and frontend tools in that step are not executed. The existing rule is widened from cards to questions.
- **Restore.** `GET /threads/{id}` returns a pending question the same way it returns a pending card (`pending_card` with its `kind`), so a reloaded page can show it again.
- The system prompt tells the model to use a question card when the user must pick between known options or settle an ambiguity, and not to use it for confirmation.
- The demo frontend and the CopilotKit example render question cards and per-row checkboxes on field-change cards. `docs/ui-components.md` documents both.

No breaking change. Clients that ignore `type` and always render a field-change card must now check `type` before rendering, because question cards arrive through the same `on_interrupt` event. A client that answers every interrupt with `{accepted}` still works for field-change cards.

## Capabilities

### New Capabilities
- `user-questions`: question cards. Covers the tool, option sources, validation of answers, delivery as an interrupt, resume forms and what the model receives.

### Modified Capabilities
- `agui-protocol`: "Confirmation cards are interrupts" and "Resuming a card" cover the question type, `answer` and `names`.
- `agent-turn`: "Confirmation pauses the turn" also covers questions and partial acceptance.
- `field-changes`: "One proposal at a time" becomes one waiting interaction per step; partial acceptance is added.
- `chat-history`: "Confirmation card status" gains `partial` and question entries (`answered` / `dismissed`); "Restore a conversation" returns a pending question too.

## Impact

- Code:
  - `backend/formguide/agent/tools.py`: `ask_user` and ToolCtx state;
  - `agent/graph.py`: the pending interaction kind, the `confirm` node handling ask and partial accept, refusing two waiting calls;
  - `agent/prompts.py`: the question rule;
  - `guide.py`: transcript entries, the structured outcome reason, status updates on resume;
  - `agui.py`: resume payload forms;
  - `transcript.py`: the docstring and `pending_card` for both kinds.
- Frontend: `frontend/src/App.tsx` and `types.ts` (question card, checkboxes), `examples/copilotkit/src/App.tsx`.
- Tests: `backend/tests/test_agui.py` and a new `tests/test_questions.py`; a live scenario in `backend/scripts/chat_harness.py`.
- Docs: `docs/ui-components.md`, `docs/architecture.md`, `docs/architecture-pages.html` (Build the UI and Integrate pages), README.
- No new dependencies.

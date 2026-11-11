# Design

## Context

The one waiting interaction today is built like this:
- `propose_changes` stores its validated changes in `ToolCtx.pending_changes`;
- the `tools` node sees that, sets `state.pending = {tool_call_id, changes, partial_errors, other_results}`, and routes to `confirm`;
- `confirm` calls `interrupt({"type": "set_fields", "changes"})` and turns the resume value into the tool result;
- `sync` closes a pending item that the user ignored.

`guide.run` turns `__interrupt__` into `CUSTOM on_interrupt`, writes a `card` transcript entry (its id becomes `card_id`), builds the structured `RUN_FINISHED.outcome`, and marks the card `accepted` or `rejected` on resume. `agui.run_kwargs` maps `resume[]` and `command.resume` into one `resume` dict. The reason for these changes is in proposal.md.

## Goals / Non-Goals

**Goals:**
- Questions reuse the existing pause and resume path end to end; there is no second mechanism.
- Old clients keep working for field-change cards.

**Non-Goals:**
- Editing a proposed value on the card before accepting it. A later change; it needs value re-validation on resume.
- Several questions in one card (a form inside the chat). One question per card keeps answers simple to validate and to explain to the model.
- Rendering rich option content (images, descriptions). `label` only.

## Decisions

### One "pending" slot with a kind

`state.pending` gains `kind: "set_fields" | "ask"`; a missing kind means `set_fields`, so checkpoints from before the change still resume. `ToolCtx` gets `pending_question` next to `pending_changes`. Each tool refuses to run when either is already set: "a card or question is already waiting for the user. One at a time." The `tools` node checks for either. Frontend tools are skipped when a `propose_changes` or `ask_user` call is in the same step; this is the existing `has_card_call` check, widened.

Alternative: a separate graph node for questions. Rejected: it duplicates routing, the ignored-card handling in `sync`, and the transcript code.

### `ask_user` validates at call time

The tool normalises options to `[{id, label}]`:
- strings become `id = label`;
- with `field`, the options are the field's canonical options from the overlay, so they respect the component's format;
- given options are matched to the field's options with `values.find_option`.

The limit is 12 options; above it the model gets a refusal that suggests `get_options` with a query, or a text question. The question text is capped at 300 characters.

### `confirm` branches on kind

For `ask`, the resume value is normalised. A dict with `answer`, or a plain string, counts as text. `accepted: false` or a `cancelled` status (which `agui` already maps to `{accepted: false}`) counts as a skip. The answer is validated against the stored options, and the tool result is a short sentence:
- "The user chose: Car loan (auto)";
- "The user chose: SMS (sms), Email (email)";
- "The user wrote: …";
- "The user skipped the question.", plus the reason when the answer was invalid.

There is no config change and no diff for a question.

For `set_fields` with `names`:
- the kept changes are `[c for c in changes if c["name"] in names]`;
- if none are kept, the card is handled as a rejection;
- the diff uses `agent_names` = the kept names;
- the text is "The user applied: a, b. Declined (not applied): c." followed by the existing diff rendering.

### Transport

`guide.run` reads `ev["value"]["type"]`:
- for `ask`, it appends a transcript entry of kind `question` with question, options, multiple, allow_text, field and status `pending`, and uses reason `ask_user` with the question in `metadata` for the structured outcome;
- on resume it sets the status from the same normalisation as `confirm`: `answered` with `answer`, or `dismissed`; for a field-change card `partial` with `names`, `accepted` or `rejected`.

That normalisation is a small shared function in `agent/interaction.py`, so the graph and the transcript always agree. `transcript.pending_card` returns the latest pending `card` or `question`, with its kind.

`agui._resume_value` keeps `{accepted}` for booleans and parses JSON strings. A non-JSON string becomes `{answer: {text}}` instead of a guessed accept/reject. A bare "yes"/"ok" string answering a field-change card is still read as accepted, because `confirm` treats an answer text in {yes, ok, accept, true} on a `set_fields` card as accepted.

### Clients

The demo `App.tsx` gets:
- a `QuestionCard` with buttons for single choice, checkboxes plus a send button for multiple, and a text input when `allow_text`;
- checkboxes on field-change card rows, ticked by default, with Accept sending only the ticked rows to the form backend plus `names`.

The CopilotKit example renders both kinds in `useInterrupt` by `type`.

## Risks / Trade-offs

- [The model overuses questions, one click per field] → the prompt rule limits questions to real choices and ambiguity; the live harness gets a scenario that fails if a plain "fill my name Anna" produces a question.
- [Old custom clients render a question as an empty field-change card] → `type` has always been in the payload; the README and the UI guide call this out; the structured `reason` differs.
- [Partial accept with a backend that recomputes dependent fields] → the frontend sends only the kept changes, and the agent's diff reflects what the backend did, as today.

## Migration Plan

Additive. Threads with a pending `set_fields` card from before the change resume as before; `kind` defaults to `set_fields`. To roll back, revert; pending questions in open threads would then be ignored as unknown and closed on the next message.

# Design

## Context

- `tool_schemas()` binds every entry of `TOOLS` on every `llm` round (`agent/graph.py`). The system prompt (`agent/prompts.py`) names the card tools in fixed bullet rules. The prompt is frozen per thread.
- `_t_ask_user` already attaches all of a field's options when the model passes none, but it rejects more than 12 (`MAX_QUESTION_OPTIONS`).
- Interactions are payloads in `ctx.pending_interaction` (kinds set_fields / ask / upload / confirm). They are resumed in `confirm` (`graph.py`), read by `agent/interaction.py` and recorded by `guide.py`.
- The widget side is `chat-card-kit` (the UX session). Shapes were agreed by message; this change is their contract.

## Goals / Non-Goals

**Goals:** one place decides which actions a run has; payload data comes from the server wherever the form knows it; old clients keep working unchanged.

**Non-Goals:** fix values on field-card rows (they stay in the review); a URL for document sources (documents have no public URL); computing payments, slots or address suggestions on the server (host callbacks in the widget).

## Decisions

1. **One resolver for actions.** `agent/actions.py: resolve(config, form, client_caps) -> frozenset[str]`. It applies the config value (true / false / auto), the auto rules (documents present, attachments enabled) and the client capabilities. `llm` binds only `TOOLS` in the set, and `system_prompt` takes the set and keeps only the bullet rules whose tool is in it.
   - The prompt is frozen per thread, so the set used for the prompt is the one from the thread's first run. A later run with fewer capabilities still unbinds the tool, and a call to an unbound tool returns a ToolError saying the client cannot show it.
   - Alternative: rebuild the prompt on every run. Rejected: that breaks the append-only history and prompt caching.
2. **Capability names map to actions and variants** in one table, `CAPS = {"review": "review_form", "ask.multi": "ask_user.fields", "sources": "sources_event", ...}`. A variant that is off is stripped from the payload or refused (for `fields`), never silently half-sent.
3. **The server derives, the model writes little.**
   - The new model-written keys are option `description` / `attrs`, `recommended`, `suggested`, `fields`, confirm `details` / `consequence`, review `warnings` / `fixes`.
   - Everything else comes from the overlay: `kind`, the range from props min / max / step / unit, all field options, consents from the pack, issues from `e.error` and warnings, document confidence from the remembered extraction.
   - The tool descriptions grow by a few lines, and no new tool appears except `review_form`.
4. **Long lists.** The 12-option cap applies only to options the model writes. Field-backed options are capped at 500; above that the question is refused with "ask in text or narrow with options".
5. **review_form in its own module** (`agent/review.py`). It computes sections from `Overlay.filled_inside` over top-level containers, and issues from `e.error`, `e.invalid_value` and required-empty fields. Model warnings are kept only for existing fields; fixes go through the same validation as `propose_changes` (`_validate_change`). The resume `fixed` reuses the accepted-card path in `confirm` (baseline, version, `render_changes`).
6. **Last extraction per thread** lives in the graph state (`last_extraction: {title, attachment_id, values: {field: [value, confidence]}}`), set by `extract_from_attachment`. `propose_changes` compares normalized values, and a match adds `confidence` and the card `source`.
7. **Events.**
   - `sources`: parsed from the researcher's final "Sources:" line by `knowledge/research.py`. The parser is pure and tested; output that cannot be parsed sends no event.
   - `receipt`: when a host tool's result is a dict with `receipt`, `tools` node emits it through the stream writer with the last confirm's card id.
8. **Feedback** goes through the transcript store as an entry `{kind: "feedback", value, card_id?}`, so it appears in `GET /threads/{id}` and needs no new storage.

## Risks / Trade-offs

- **Prompt frozen vs capabilities changing mid-thread.** This is rare (same client), and the ToolError covers it.
- **Model-written attrs can be made up** (rates, payments). The prompt tells the model to take numbers only from the documents or the form, and the widget shows a "from the documents" note when sources exist.
- **500 options in one payload** (about 20 KB) is acceptable for a card. Bigger lists stay text questions.
- **Matching extracted values** by normalized string can miss reformatted values. A miss only drops the confidence mark.

# Proposal

## Why

The user picked 17 richer chat cards (the widget side is the `chat-card-kit` change). Most of them need data the backend does not send yet: field kinds, option details, all options of a long list, number ranges, consents, a form review, document confidence, sources and confirm details. At the same time every action must be switchable off per deployment, and the model must not get more tools to choose from. Today all 13 built-in tools are bound on every turn, whatever the deployment or the client can show; a client without an upload renderer still gets `request_file`, and the turn gets stuck.

## What Changes

- **Actions config.** `actions: {ask_user, request_file, confirm_action, focus_field, review_form, ask_documents, extract_from_attachment}` with `true`, `false` or `auto`. An action that is off is not bound, and its prompt rules are left out. `auto`: `ask_documents` only when the form has documents, `extract_from_attachment` and `request_file` only when attachments are enabled.
- **Client capabilities.** The client may send `forwardedProps.capabilities` (a list such as `ask.details`, `review`, `sources`). The effective set is config ∩ capabilities. Without the list, everything the config allows stays on, so existing clients keep working.
- **Richer payloads, derived by the server where it can.** The model writes only what it alone knows:
  - every proposed change carries `kind` (the field role);
  - ask_user options may carry `description`, `attrs` and `recommended`, and the question may carry `suggested`;
  - a field-backed question attaches all the field's options (up to 500), while the model's own options stay at 12 or fewer;
  - a number question gets `min` / `max` / `step` / `unit` from the field;
  - a new input type `address`;
  - ask_user `fields`: 2-3 short fields in one question, validated like proposals, resumed with `answers` and the new config.
- **Consents.** Bool fields marked as consents (domain pack or field spec) are proposed unticked, with their document, and only ticked rows are applied.
- **review_form** (one new tool, behind `actions.review_form` and the `review` capability):
  - the server computes progress by section and the blocking issues (required empty, validation errors, values not in options);
  - the model may add warnings and fix values, which are validated;
  - it is an interrupt of type `review`, resumed with `continue`, `submit` or `fixed`.
- **Soft row issues.** propose_changes may carry a short `issue` per change when a rule or document flags a valid value (rules are free text, so the model notices them); the row shows it as a warning.
- **Document source.** Changes whose values match the thread's last extraction carry `confidence`, and the card a `source` header.
- **Sources.** After an answer that used `ask_documents`, a CUSTOM `sources` event lists the documents and sections it cited.
- **Confirm details and receipt.** `confirm_action` takes `details` and `consequence`. When a host tool returns `{receipt: …}`, a CUSTOM `receipt` event follows.
- **Feedback.** `POST /feedback {thread_id, value, card_id?}`, stored with the transcript.
- **Privacy note.** `attachments.privacy_note` is sent with upload requests as `privacy`.

## Capabilities

### New Capabilities
- `form-review`: the review_form tool and its review interrupt: progress by section, issues, fixes and the resume shapes.
- `agent-actions`: which actions the agent has: the actions config, the auto rules, client capabilities and their intersection.

### Modified Capabilities
- `user-questions`: option details, comparison attributes, suggested options, field-backed long lists, number ranges from the field, the address input, several fields in one question.
- `field-changes`: `kind` on every change, consent rows, soft row issues, document source and confidence.
- `action-confirmations`: details and consequence; the receipt event.
- `document-research`: the sources event.
- `attachment-extraction`: the privacy note in upload requests; the remembered last extraction.
- `domain-packs`: consent fields.
- `http-api`: the feedback endpoint.

## Impact

- Backend: `formguide/agent/tools.py`, `agent/prompts.py`, `agent/graph.py`, `agent/interaction.py`, `guide.py`, `agui.py`, `config.py`, `domain/packs.py`, `server.py`, `transcript.py`. A new `agent/review.py`. Tests in `backend/tests/`.
- Wire: new optional payload keys and two CUSTOM events (`sources`, `receipt`). Nothing is removed; clients that ignore the keys keep working.
- Widget: built by the UX session in `chat-card-kit` against these shapes.
- Docs (`site/`): reference/configuration (actions, privacy note), reference/agui-events (payload keys, events, capabilities), reference/http-api (feedback), concepts/turn and architecture.

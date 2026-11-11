# Proposal

## Why

The chat the user sees is rebuilt from the model's history. Compaction rewrites that history, and the default checkpointer lives in memory, so the conversation disappears from the UI after a long chat, a page reload or a server restart. Users fill long forms over several sittings: they leave and come back, and expect their conversation (and a pending confirmation card) to still be there.

## What Changes

- Add a **display transcript** per thread, separate from the model's history: what the user saw (their messages and attachments, the assistant's replies, tool activity, confirmation cards with their status, errors, notices). Compaction never touches it.
- Record the transcript inside `FormGuide.run`, so every transport gets it.
- Make history durable: a file-backed transcript store and an SQLite checkpointer, configurable in code and YAML; the demo uses both.
- Add `GET /threads/{thread_id}` (transcript + pending card) and `DELETE /threads/{thread_id}` to the router.
- Demo frontend: remember the thread per form, restore the chat on reopen (including a pending card that can still be answered), and a "New chat" action. The demo also keeps the form's values in the browser to stand in for the form backend's own persistence.

## Capabilities

### New Capabilities
- `chat-history`: the user-facing transcript of a conversation, how it is recorded, persisted and restored.

### Modified Capabilities
- `http-api`: endpoints to restore and delete a thread.
- `model-configuration`: configurable persistent stores (checkpointer, transcript store).

## Impact

- New module `formguide/transcript.py`; changes to `guide.py`, `config.py`, `server.py`.
- New dependency `langgraph-checkpoint-sqlite` (with `aiosqlite`).
- Demo: `formguide.yaml`, `frontend/src/App.tsx`, `frontend/src/api.ts`.
- Docs: `docs/architecture.md`, architecture pages (long conversations page), README.

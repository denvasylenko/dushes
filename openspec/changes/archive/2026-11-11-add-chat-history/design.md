# Design

## Context

The graph state holds the model's history as LangChain messages. It is optimised for the model: per-turn form context blocks, tool results, and after compaction a memory note instead of old turns. The UI must not depend on it.

## Goals / Non-Goals

**Goals:**
- The user sees the whole conversation after reopening the form, regardless of compaction.
- A pending confirmation card survives a reload or restart and can still be answered.
- Persistence is configurable; nothing provider- or framework-specific in the core.

**Non-Goals:**
- Persisting the form's values: that is the form backend's job (the demo fakes it in the browser).
- Multi-device sync, authentication or per-user access control of threads.

## Decisions

- **Two histories.** The model history (checkpointer) and the display transcript (TranscriptStore) are independent. Alternative considered: render the UI from the checkpointer and keep compacted turns there; rejected because it couples UI to the model's context policy and grows the model's input.
- **Record in `FormGuide.run`.** The run loop already sees every event (text, tool activity, interrupts, errors, memory notices), so recording there covers the FastAPI router and any custom transport. Each card gets a `card_id` (added to the `on_interrupt` value) so its status can be updated on resume.
- **Card status transitions.** `pending → accepted | rejected` on resume; `pending → dismissed` when a new message arrives first (matching the graph, which closes the proposal).
- **Stores.** `TranscriptStore` protocol with `FileTranscriptStore` (one JSONL file per thread; update rewrites the small file) and `MemoryTranscriptStore`. Checkpointer: any LangGraph saver; helper for SQLite (`AsyncSqliteSaver`, lazily connected). Library default stays in memory; the demo uses files + SQLite under `data/`.

## Risks / Trade-offs

- JSONL rewrite on update is O(n) per card update; fine for chat-sized threads. A database-backed store can implement the same protocol.
- Transcript and checkpointer can drift if one store is wiped; restoring shows the transcript, and the next message starts the model from whatever the checkpointer has.

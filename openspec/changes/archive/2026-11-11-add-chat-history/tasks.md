# Tasks

## 1. Library

- [x] 1.1 Add `formguide/transcript.py`: `TranscriptStore`, `FileTranscriptStore`, `MemoryTranscriptStore`
- [x] 1.2 Record the transcript in `FormGuide.run` (user, assistant, tool, card + status, error, notice) and add `card_id` to `on_interrupt`
- [x] 1.3 `FormGuide.thread(thread_id)` and `FormGuide.delete_thread(thread_id)`
- [x] 1.4 Config: `transcripts` store and `checkpointer` (`{sqlite: path}` in YAML) + `sqlite_checkpointer()` helper

## 2. HTTP

- [x] 2.1 `GET /threads/{thread_id}` and `DELETE /threads/{thread_id}` in `create_router`

## 3. Demo

- [x] 3.1 `demo/formguide.yaml`: SQLite checkpointer and file transcripts under `data/`
- [x] 3.2 Frontend: thread per form in local storage, restore chat and pending card, "New chat", keep form values and open sections in the browser

## 4. Verification and docs

- [x] 4.1 Tests: transcript recording, card status transitions, compaction does not touch the transcript, persistence across a FormGuide restart with SQLite (resume a pending card)
- [x] 4.2 Live check: reload the page mid-conversation and restart the server
- [x] 4.3 Update `docs/architecture.md`, architecture pages, README; validate specs; check English

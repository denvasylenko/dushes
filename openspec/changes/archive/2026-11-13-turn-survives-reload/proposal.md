# Proposal

## Why

A turn runs only while the HTTP response is open. When the user closes the tab, reloads, or a phone unloads the page in the background (iOS does this when another app opens), the server cancels the turn midway: the answer is lost and an action the agent had started (a card, a search) is left undone. On a long form filled from a phone this throws the user's work away.

## What Changes

- **Server**: a turn runs as a background task, separate from the response that streams it. Closing the connection no longer stops the turn; it finishes and records its result in the thread's transcript as usual. A new turn for the same thread waits for a running one to finish. `POST /stop {thread_id}` stops a running turn (the chat's Stop button calls it), since closing the connection no longer does.
- **Restore**: `GET /threads/{id}` says `running: true` while a turn is still in progress.
- **Widget (formguide plugin)**: after a reload, a running turn shows as "Still answering…" under the restored messages; when it finishes, the chat shows the answer and the card without a reload. Stop also tells the server.

Not in this change: re-attaching to the live stream (the answer appearing word by word after a reload); the result appears when the turn completes.

## Capabilities

- `http-api`: turns outlive the connection; the stop endpoint.
- `chat-history`: `running` on restore.
- `chat-widget-formguide`: a running turn after a reload; Stop on the server.

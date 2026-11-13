# Tasks

- [x] 1. Guide: `run_detached` runs a turn as a background task fed to the response; waits for a running turn of the same thread; `stop(thread_id)`; `running` in `thread()`.
- [x] 2. Router: `/run` uses it; `POST /stop`.
- [x] 3. Plugin: `restore` returns `running`; the element shows "Still answering…" and checks back until the turn ends, then restores; Stop posts `/stop`.
- [x] 4. Tests: a turn finishes after the client goes away; stop; restore while running; the widget's waiting line.
- [x] 5. Docs: persistence / chat history page, the HTTP reference, the widget guide.

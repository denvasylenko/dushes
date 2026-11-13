## Why

Readers could not see what the chat's cards look like without running the demo and steering the agent to each one. Backend pages carried browser code and frontend pages carried server commands and keys, configuration was shown only as YAML, the prefill response was unexplained, the CopilotKit guide led with a development-only option, and the docs assistant could not answer "where is X documented".

## What Changes

- A card gallery page: every card and variant as a live specimen (the shipped renderer replaying a recorded event), with the event and the answer it sends back.
- Backend pages show server code only (YAML and Python tabs, HTTP calls); browser code moves to the frontend pages, which no longer show server commands or keys.
- Every backend and widget page ends with an "Every option" section; the models guide shows each provider in YAML and Python.
- Prefill documents its input and response field by field; the CopilotKit guide leads with CopilotKit's runtime and keeps the direct connection as a prototype.
- The docs assistant gets the table of contents with every question and answers "where" questions with page links first.

## Impact

- `site/` (pages, `CardGallery.astro`, `src/demo/gallery.ts`, sidebar), `backend/docs_ai/` (corpus table of contents, prompt), `backend/tests/test_docs_ai.py`.

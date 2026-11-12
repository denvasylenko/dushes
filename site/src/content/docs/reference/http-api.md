---
title: HTTP API
description: Every endpoint of formguide's FastAPI router, with its body and answer.
---

`create_router(guide)` mounts these under your prefix (`/agent` with `create_app` and `formguide serve`). Errors are JSON `{"detail": "..."}`. Nothing here authenticates: put your own auth in front.

| Method and path | Body | Answer |
| --- | --- | --- |
| `POST /layouts` | `{jsx, form_id?, domain?, config?}` | `{jsx_hash, ...}` plus warnings; `config` (a sample `{props, state}`) adds value-format warnings. 413 when the JSX is too large |
| `GET /layouts/{jsx_hash}` | | `{jsx_hash}`, or 404 when unknown (register again) |
| `POST /run` | an AG-UI `RunAgentInput` | an AG-UI event stream (SSE, or the protocol's binary encoding by `Accept`). 422 when the body is not a `RunAgentInput`; 409 when `state.jsx_hash` is unknown |
| `POST /prefill` | `{state, data?, text?, attachment_ids?, thread_id?}` | validated values to prefill, without a chat |
| `POST /attachments` | multipart: `thread_id`, `file` | the stored attachment `{id, ...}` for the next run's `state.attachments` |
| `GET /kb/{form_id}` | | `{documents, namespaces, compiled}` in the form's scope |
| `POST /kb/{namespace}/documents` | multipart: `files` (repeat) | `{added, documents}` |
| `DELETE /kb/{namespace}/documents/{doc_id}` | | `{documents}`, or 404 |
| `POST /kb/{form_id}/compile` | `{jsx, config}` | compiles the documents in scope into the form's domain pack |
| `GET /threads/{thread_id}` | `?format=agui` `&form_id=` | the display transcript and the pending card; with `format=agui`, `{thread_id, messages, pending_card, starters?}` for `agent.setMessages` |
| `DELETE /threads/{thread_id}` | | `{deleted}` |
| `POST /feedback` | `{thread_id, value: 1 \| -1, card_id?}` | 204; kept in the thread's transcript as a `feedback` entry. 422 for any other value |
| `GET /debug/{thread_id}` | | the model's history and recent run stats; only with `debug=True` |

## The run request

`POST /run` takes the AG-UI input as is. formguide reads:

| Field | Meaning |
| --- | --- |
| `threadId` | the conversation |
| `messages` | the last user message is the new turn; `tool` messages answer frontend tools |
| `state` | `{config, jsx_hash, form_id, ui?, attachments?}`: the form as your backend last built it |
| `tools` | frontend tools for this run |
| `forwardedProps.command.resume` | the answer to a card (legacy mode) |
| `resume[]` | the answer to a card (AG-UI 1.0 structured mode): `{interrupt_id, status: "resolved", payload}` or `status: "cancelled"` |
| `traceparent` / `tracestate` headers, or `forwardedProps.traceparent` / `tracestate` | the caller's W3C trace context: with `tracing.otel` the turn span joins that trace; ignored otherwise |
| `forwardedProps.capabilities` | the cards and variants the client renders ([AG-UI events](../agui-events/#capabilities)); absent = all |
| `forwardedProps.prefill` | `{data?, text?, attachment_ids?, language?}`: values the app already knows |

What comes back is in [AG-UI events](../agui-events/). Behaviour contract: [http-api](../../specifications/http-api/), [agui-protocol](../../specifications/agui-protocol/).

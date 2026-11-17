---
title: HTTP API
description: Every endpoint of Dushes' FastAPI router, with its body and answer.
---

`create_router(guide)` mounts these under your prefix (`/agent` with `create_app` and `formguide serve`). Errors are JSON `{"detail": "..."}`. Nothing here authenticates: put your own auth in front.

| Method and path | Body | Answer |
| --- | --- | --- |
| `POST /layouts` | `{jsx, form_id?, domain?, config?}` | `{jsx_hash, ...}` plus warnings; `config` (a sample `{props, state}`) adds value-format warnings. 413 when the JSX is too large |
| `GET /layouts/{jsx_hash}` | | `{jsx_hash}`, or 404 when unknown (register again) |
| `GET /models` | | `{choices: [{name, label, default, usable, model}]}`: the model choices a run may name (`models.choices`); an empty list on a server without choices |
| `POST /run` | an AG-UI `RunAgentInput` | an AG-UI event stream (SSE, or the protocol's binary encoding by `Accept`). The turn finishes even if the client goes away. 422 when the body is not a `RunAgentInput`; 409 when `state.jsx_hash` is unknown |
| `POST /prefill` | `{state, data?, text?, attachment_ids?, thread_id?}` | validated values to prefill, without a chat |
| `POST /attachments` | multipart: `thread_id`, `file` | the stored attachment `{id, ...}` for the next run's `state.attachments` |
| `POST /transcribe` | multipart: `file` (the recording: webm, mp4, ogg, wav), `language?` (`ru`, `ru-RU`) | `{text, language}`; 501 without `transcription` in the config, 413 over `max_bytes`, 502 when the model fails. The site router serves it too |
| `GET /kb/{form_id}` | | `{documents, namespaces, compiled}` in the form's scope |
| `POST /kb/{namespace}/documents` | multipart: `files` (repeat) | `{added, documents}` |
| `DELETE /kb/{namespace}/documents/{doc_id}` | | `{documents}`, or 404 |
| `POST /kb/{form_id}/compile` | `{jsx, config}` | compiles the documents in scope into the form's domain pack |
| `GET /threads/{thread_id}` | `?format=agui` `&form_id=` | the display transcript, the pending card and `running` (a turn still in progress); with `format=agui`, `{thread_id, messages, pending_card, running, starters?}` for `agent.setMessages` |
| `POST /stop` | `{thread_id}` | `{stopped}`: ends the thread's running turn (a turn outlives its connection, so closing the stream does not stop it) |
| `DELETE /threads/{thread_id}` | | `{deleted}` |
| `POST /feedback` | `{thread_id, value: 1 \| -1, card_id?}` | 204; kept in the thread's transcript as a `feedback` entry. 422 for any other value |
| `GET /debug/{thread_id}` | | the model's history and recent run stats; only with `debug=True` |

## Dushes (the site assistant)

`create_dushes_router(dushes)` mounts these under your prefix (`/site` in the demo). Errors are JSON `{"detail": "..."}`.

| Method and path | Body | Answer |
| --- | --- | --- |
| `POST /run` | an AG-UI `RunAgentInput` with `state: {page: {path, title}, form?}` (`form` is the form state on a form page) | an AG-UI event stream: Dushes' answer, or the UI agent's events on a form page; `CUSTOM site_directive` when it moves the user |
| `GET /map` | | the site map the page renders or checks |
| `GET /threads/{thread_id}` | `?form_id=` | the site chat for the page after a reload: its messages and, on a form page, the form's open card |
| `POST /transcribe` | multipart: `file`, `language?` | as above, for dictation in the site chat |

## The run request

`POST /run` takes the AG-UI input as is. Dushes reads:

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
| `forwardedProps.model` | a name from `GET /models`. The conversation keeps the choice of its first run. Before the stream starts: 422 `{detail, choices}` for an unknown or unusable name, 409 `{detail, code: "model_fixed", choice}` when the conversation already runs on another choice |
| `forwardedProps.prefill` | `{data?, text?, attachment_ids?, language?}`: values the app already knows |

What comes back is in [AG-UI events](../agui-events/). Behaviour contract: [http-api](../specifications/http-api/), [agui-protocol](../specifications/agui-protocol/).

## Voice mode (experimental)

A separate router, `create_voice_router`, mounted by the host (the examples use `/voice`) only when it has voice codes. The pass from `unlock` travels in the `X-Voice-Pass` header of every other call.

| Method and path | Body | Returns |
| --- | --- | --- |
| `POST /voice/unlock` | `{code}` | `{person, pass}`; 403 for a wrong code |
| `POST /voice/session` | `{sdp, thread_id}` | `{talk, sdp, contract, limits}` (a browser, WebRTC); 429 `{reason}` when it may not start |
| `GET /voice/events?talk=` | | the conversation's events (SSE) |
| `POST /voice/end` | `{talk}` | `{cost_usd}` |
| `WebSocket /voice/stream?thread_id=` | | audio both ways (binary PCM16 mono, 24 kHz) and the events as text frames, for a native app |

The events, the limits and the settings: [Voice mode](../../agents/shared/voice/).

## Experimental features

A separate router, `create_experiments_router`, mounted by the host (the examples use `/experiments`) only when it has `EXPERIMENT_CODES`.

| Method and path | Body | Returns |
| --- | --- | --- |
| `GET /experiments` | | `{features, unlocked}`: what a code opens here, and whether this request holds a valid pass |
| `POST /experiments/unlock` | `{code}` | `{person, pass, features, passes}`; 403 for a wrong code. `passes`: one pass per feature the code opens (`decision_model`, `voice`) |

The decision model's pass goes in the `X-Experiment-Pass` header of each run. More: [Experimental features](../../agents/shared/experimental-features/).

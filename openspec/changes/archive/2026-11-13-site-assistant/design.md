# Design

## Context

`FormGuide.run(thread_id, message|resume|prefill, state)` is a complete turn as AG-UI events, with its own checkpointer and transcript per thread. The demo frontend renders mock forms from JSX and talks to the form agent through `<agui-chat>` and the formguide plugin.

## Goals / Non-Goals

**Goals:**
- one chat across a multi-page site;
- answers from the site's content;
- navigation to pages, tabs and sections;
- a hand-off to the form agent that needs no repeat;
- the form agent unchanged.

**Non-Goals:** reading arbitrary forms from the DOM (a later step: a page adapter producing the form contract); crawling a real site (the site map is a file here); restoring the site chat after a full page reload (the demo is a single-page app).

## Decisions

1. **Delegate, do not embed.**
   - On a form page the router calls `FormGuide.run` with the thread id `<site thread>-<form id>` and passes its events through. The form agent keeps its own history, frozen prompt and cards per form.
   - Alternative: the form graph as a LangGraph subgraph. Rejected for now: it needs changes inside the form agent's state, and the product rule is to leave it alone.
2. **Router.**
   - `resume` goes to the form agent (only it shows cards).
   - On a page without a form, the turn goes to the site agent.
   - On a form page, a cheap classification decides: words of navigation or other pages ("go to", "open", a page title, "contacts", "FAQ") send the turn to the site agent, everything else to the form agent. Optionally a one-word model call (`router_model`) for unclear cases; on failure it falls back to the form agent.
3. **Site agent** is a tool loop like Ask AI's, with the site's sections as passages, a short history of the site thread and three tools. `navigate` and `open_form` are checked against the site map; an unknown path is refused, so the model cannot invent pages.
4. **Hand-off.**
   - `open_form` stores a note per site thread and emits `site_directive {type: "navigate", path, form_id}`.
   - The page opens the form and runs the chat with `forwardedProps.handoff: true`.
   - The router then calls `FormGuide.run` with the note as the first message ("[Handed over by the site assistant] On the site the user said: ..."). Prefill was tried first, but its text extraction is written for documents and returned nothing for a sentence; a message needs no change to the form agent.
5. **Directive** `CUSTOM site_directive {type: "navigate", path, tab?, section?, form_id?}`: the page changes route, opens the tab or accordion, scrolls to the section and rings it.

## Risks / Trade-offs

- **Keyword routing on form pages** can misroute an ambiguous message. The model fallback and the site agent's `open_form` back to the same form keep the user moving; tests cover the common phrasings.
- **Two transcripts** (site and per form) are fine for the demo; a unified view is a later step.

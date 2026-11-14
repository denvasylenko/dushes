# Proposal

## Why

Dushes knows the site only from the site map written in advance and the host's `context` text: it cannot see what is on the user's screen right now (a tariff table, a cabinet dashboard, a product card, the text the user selected), so "explain this table" or "what does this number mean" gets a vague answer. A form already sends its config with every message; a page should be able to do the same, and pages whose host prepares nothing should still work.

## What Changes

- **First (phase 0, from QA's round 1): the form agent sees the page it sits on.** On a page with a form, Dushes leaves form questions to the form agent (`stay_on_forms`), but the form agent never got the page's own text, so it denied facts the page states (a 27.90 EUR fee, visa fees, a deposit; about nine scenarios at -3 to -5, one held out). Dushes passes the current page's facts (the site map's sections for this path, and later `state.page.content`) to `FormGuide.run(page=...)`; the form agent reads them in a `<page_facts>` block of the current message (never the frozen system prompt, so the cache holds), cut to `max_chars`, as data, never instructions. Its prompt gets one rule: what the page states is as good as the form; never say the page or the form does not give a fact that `<page_facts>` holds. A host without Dushes may pass `state.page.content` directly.

- A page config: `state.page.content` (sections with text and tables, the visible section, the selection, free data), prepared by the host like the form config. This is the main path.
- A fallback snapshot: when the host sends no page content, `<agui-chat>` (attribute `page-snapshot`) attaches a compact snapshot of the visible page as `state.page.snapshot` (title, headings, visible text, tables, selection), skipping inputs, passwords and elements marked `data-agui-skip` or matched by configured selectors.
- Dushes gets the page in a `<page_context>` block of the current message (not the frozen system prompt), cut to a configured size with the visible section first, and treats it as data, never as instructions.
- A `highlight` tool: Dushes can point at a section or element on any page (not only form fields); a valid call emits `site_directive {type: "highlight", ...}`, checked against the ids the page sent and the site map.
- Configuration: `page_context: {mode: host | snapshot | both | off, max_chars, skip}` in the site map and as a `Dushes(...)` argument.

## Capabilities

### New Capabilities
- `page-context`: what the page tells Dushes about the screen (host page config and widget snapshot), how it reaches the model, its limits and privacy rules, and pointing at things on the page.

### Modified Capabilities
- `dushes`: answers may also come from the current page, and Dushes may highlight parts of it.

## Impact

- Backend: `backend/formguide/site/` (page context rendering, the `highlight` tool and directive, the site map's `page_context` key).
- Widget: `packages/agui-chat` (the `page-snapshot` attribute and the snapshot collector; owned by the UX/UI session, coordinate before editing).
- Demo: `frontend/src/site/Site.tsx` (send page content on one page, handle the highlight directive), `backend/demo/site.yaml`.
- Docs: `backend/dushes.mdx`, `frontend/dushes.mdx`, `reference/agui-events.md`, `reference/agui-chat.md`, `form/contract.mdx` (the `site_directive` type), `concepts/architecture.md`.
- No breaking changes: without page content and without the attribute everything works as today.

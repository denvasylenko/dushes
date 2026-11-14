# Proposal

## Why

Hosts want Dushes to help a business owner grow, not only answer: say the one thing worth doing today, draft a reply the owner sends themself, and back every recommendation with where it comes from. The first host is the Herefront cabinet (its change `add-owner-growth-coach`, group 4). Today Dushes speaks only when asked, cannot show cards and has no sources of its own. Everything business-specific (what to recommend, the data) stays with the host; Dushes gets three generic abilities.

## What Changes

- **An opening turn with one tip.** The page runs Dushes with `forwardedProps.opened: true` when the user opens the chat. In that run Dushes has a `tip(topic, text, why)` tool and may say one thing worth doing now, from the host's live facts and tools, or stay silent. The server keeps a ledger in the thread: at most `tips.per_day` tips a day (default 1), a topic the user declined stays quiet `tips.snooze_days` (default 7), the same topic is never repeated the same day. When a tip is pending, Dushes has `tip_feedback(topic, later)` to record "not now" from whatever the user answers, in any language.
- **The host can own the ledger and the candidates.** `tips_ledger=(seen(ctx) -> [{topic, at, declined}], record(ctx, topic, declined))` lets Dushes and the host's other channels (a morning bot message, a "Today" card) keep one journal, so "not now" anywhere quiets the topic everywhere; without it the ledger is per thread. `tip_candidates(ctx) -> [topics]` names the topics worth raising now; an empty list means silence without calling the model, and the model only words one of the candidates.
- **Cards from blocks for Dushes.** `Dushes(cards=[...])` (the same specs as the form agent's `cards`, display cards only for now): each becomes a `show_<type>` tool. A host builds its "reply draft" card from existing blocks: the text, `links` with copy and send-as-message (WhatsApp), the source.
- **Sources from host tools.** A `SiteTool` handler may return `{text, sources: [{title, section?}]}`; Dushes then sends CUSTOM `sources` under its answer (the widget already draws them). The prompt says a recommendation names its source or says it is general practice.

Not in this change: scheduled messages outside an open chat (the host's bot does those), cards that wait for an answer in Dushes.

## Capabilities

- `dushes`: the opening turn, the tips ledger, cards from blocks, sources from host tools.

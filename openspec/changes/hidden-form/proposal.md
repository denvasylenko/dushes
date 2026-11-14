# Proposal

Status: idea (asked for by the CPO, 2026-11-15). Not promised on any docs page.

## Why

A host may run a form that the person never sees: the page shows only the chat, and the agent collects the values with cards and sends them with the host's tool (the "chat-only form" recipe). Today the only thing that tells the agent so is a sentence the host writes in the pack's `flow_hints` ("The person does not see this form..."). It works (QA: 20 of 20 without a "look at the form" phrase), but it depends on each host's wording, and the core still offers tools that make no sense there.

## What Changes

- **The page says it**: `ui.form_visible: false` in the run's state (the widget's formguide plugin gets the option `formVisible: false`; a `schemaForm` held in memory sets it by itself). Absent or true: as today.
- **The core follows**: with a hidden form the agent's context says so in one line; `focus_field` is not offered (there is nothing to point at); the prompt's "show where" rules are dropped for the turn; the agent reads values back in the chat and on cards, and never names a field's place, a tab or a button on the page.
- **Cards stay the same**: field-change and question cards work as now (the user confirms values on the card); `review_form` lists what is left in the chat's card.
- **A host's own flow hint is no longer needed** for this; it still wins where it says more.

## Capabilities

### Modified Capabilities
- `agent-turn`: a form the person does not see.

## Impact

`agent/actions.py` (focus_field off for the turn), `form/render.py` (the context line), prompts (one rule), the widget's plugin option (widget designer), docs (the chat-only recipe drops the flow-hint advice), QA: the chat-only recipe without the flow hint must still score 20 of 20.

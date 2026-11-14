# Proposal

## Why

A long turn (reading documents, a hand-off, several tool rounds) shows dots and "Still working…" for up to half a minute. The user cannot tell whether anything is happening. A short checklist of what the agent is about to do, ticked as it goes, makes the same wait feel like progress.

## What Changes

- A built-in tool `show_plan(steps)` for the form agent and Dushes: for a turn that needs three or more steps, the model calls it alongside its first tool calls with two to five short labels in the user's language.
- The run emits CUSTOM `plan {plan_id, steps: [{label, state}]}` and updates it: the server marks one step done per finished tool round and every step done when the answer starts; a failed turn marks the current step failed.
- `<agui-chat>` shows the plan as a checklist in place of the dots; without a plan it behaves as today.
- The plan is display only: it never enters the model's history beyond the tool call itself, and it is recorded in the transcript as a finished checklist.

## Capabilities

### New Capabilities
- `turn-checklist`: the plan a long turn shows, how it advances, and how the chat displays it.

### Modified Capabilities
(none)

## Impact

- Backend: `agent/tools.py` and `agent/graph.py` (the tool and the event), `site/agent.py` (the same tool for Dushes), prompts (when to plan).
- Widget: the checklist in `packages/agui-chat` (coordinate with the UX/UI session); a card-gallery specimen.
- Docs: `reference/agui-events.md`, `frontend/chat-widget.mdx`, `concepts/turn.mdx`, the landing demo script if it shows a long turn.

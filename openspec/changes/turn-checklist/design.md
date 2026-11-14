# Design

## Context

The widget shows tool calls as steps and `tool_progress` sub-steps under a running tool, but before the first tool result and between rounds the user sees only a spinner. The model knows its plan; the server knows when rounds finish.

## Goals / Non-Goals

**Goals:** a plan in the user's words at almost no extra latency.

**Non-Goals:** no separate planner model; no exact mapping of steps to tool calls.

## Decisions

- **The model plans, the server ticks.** `show_plan` goes out in parallel with the first tool calls, so it adds no round. Ticking per finished round is approximate but honest and needs no extra calls. Alternative: a separate planner model; rejected, an extra call before every long turn. Alternative: the model ticks steps itself; rejected, one tool call per tick.
- **One event name, full state each time.** Every `plan` event carries all steps, so a client that missed one still draws the right state.
- **Display only.** The tool result is "Shown." and the plan is not repeated in later context.

## Risks / Trade-offs

- [More rounds than steps] → the last step stays active until the answer starts.
- [Fewer rounds than steps] → all steps tick done when the answer starts.
- [The model plans trivial turns] → the prompt rule and a test that a no-tool turn emits no plan.

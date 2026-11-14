# Design

## Context

Cards carry `previous` / `previous_display` per row, and the confirm node knows which rows the user kept (`names`) and edited (`edited`). The transcript already records card status for display.

## Goals / Non-Goals

**Goals:** a reliable list of what changed and a safe way back.

**Non-Goals:** no automatic revert without a card; no history of the user's own typing in the form (only what went through the chat); no widget history sheet in this change.

## Decisions

- **Record at the confirm node**, where kept and edited rows are known; edited values are recorded as the user's final values.
- **Store next to the transcript**, keyed by thread and form, so it survives restarts like the chat. Alternative: inside the checkpointer state; rejected, the endpoint must read it without the graph.
- **Undo is a proposal.** The agent reuses `propose_changes` with previous values; validation (visibility, options, read-only) applies as for any change. Alternative: a dedicated revert action; rejected, it would bypass the card and its validation.
- **Dependent fields** come from the dependencies already learned from diffs: the card includes fields that changed in the same form reaction.

## Risks / Trade-offs

- [The previous value is no longer valid (options changed)] → validation rejects it and the agent says so.
- [Long histories] → `list_changes` returns at most `limit` (default 20) rows.

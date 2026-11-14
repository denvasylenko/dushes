# Design

## Context

`SiteTool(name, description, parameters, handler)` returns text only. The form agent already has `confirm_tools` (a held call with a confirmation card and `receipt`), and blocks cards with host buttons (`card-blocks`).

## Goals / Non-Goals

**Goals:** reuse the form agent's confirmation, receipt and blocks cards for Dushes, with the same events.

**Non-Goals:** no generic "action agent"; no automatic sending of messages or payments by Dushes.

## Decisions

- **Undo lives on the tool.** `undo(args, ctx)` sits next to `handler`, so the host defines both halves together; formguide stores `(tool, args, host ctx id)` under a random `undo_id` for one hour.
- **Same events as the form agent.** `receipt`, blocks cards and the confirmation card keep their shapes, so the widget needs no new renderer.
- **Held tools end the turn.** Like the form agent's interrupt: the card is the turn's end; the answer resumes it. This needs Dushes to support a resumable card, which this change adds for the confirmation card only.

## Risks / Trade-offs

- [Undo after the data changed elsewhere] → the host's `undo` decides and returns its own text; formguide only guarantees one call.
- [Resumable cards in Dushes are new] → limited to confirmation here; questions and comparison cards come with their own changes.

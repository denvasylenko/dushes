# Proposal

Internal. Only we use it for now (the owner, through the CPO, 2026-11-17): there is no configuration surface for
outside developers and no page on the docs site.

## Why

The owner: every move, pick and choice, everything but free text, can be made by a fast chooser, and only free
text needs the AI. The CTO's decision D-29 (2026-11-17, recorded in the Cheese repository's `docs/decisions.md`):
a fast choice layer in front of the agent, living in this package as a shared capability of the site agent and
the form agent. The supplier of the choosing model is behind an interface and is picked only after a measurement.

Today every phrase, including "open requests" and "tomorrow at eight", takes a whole agent turn: seconds where a
choice among known options takes a fraction of one.

## What Changes

- A choice layer that runs before the agent on a typed or spoken phrase. Its questions are generated from what
  the package already knows: the form (a dropdown or radio becomes a choice, a date a date choice, a checkbox a
  yes / no) and the screen map (screens and their elements become a choice).
- One contract: a phrase, its language, the options `{id, label}` (255 at most) and the screen go in; `{id or
  none, confidence}` comes out. Implementations are swappable behind it, in this order: rules, embeddings, an
  external chooser, the agent. A host never names a supplier.
- A deadline of about 300 ms. Late, unsure, failed or switched off: the turn goes to the agent as today. Nothing
  depends on the layer being there.
- By itself the layer only looks (opens, shows, scrolls) and makes reversible edits with Undo. Anything
  destructive goes through the confirmation rule (D-28), unchanged.
- Out goes only the person's phrase and the option labels. Guests' names and phones are never options and never
  sent; real phrases go to an external supplier only under a data processing agreement.
- Internal settings only: the supplier (`jev | haiku | rules | off`), the confidence threshold, the deadline, the
  kinds that act by themselves, and what is never sent.

The first step is groups 1 to 4 (the owner's yes): understanding, navigation, values, routing. Group 5
(suggestions with search, trimming the context, checking an answer, guests' requests) is later and not here.

## What does not change

No supplier's client is written in this change. The external chooser's client is written only after the QA
Lead's measurement passes the bar (confident wrong picks at most 1%, at least 60% of choice turns covered, p95 at
most 300 ms from `fra`) and the owner says yes to that supplier by name. Embeddings need a dependency this
package does not have; that too is the owner's yes. Models, limits, the money brake and the confirmation of
destructive actions are untouched.

## Impact

- New: `backend/formguide/intent/` (the contract, the question generator, the rules implementation, the settings).
- `backend/formguide/site/guide.py` and `backend/formguide/guide.py`: the layer is asked first; the agent runs
  when it says none.
- Every call to a paid supplier is counted in the run's stats, as model calls are.
- Specs: a new capability `intent-layer`. No docs-site page while it is internal.

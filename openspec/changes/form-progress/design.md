# Design

## Context

The form context already counts `required filled 3/55` per form, and Dushes' site thread already records every form's turns with `form_id`. The real form values live in the form backend; formguide never stores the config.

## Goals / Non-Goals

**Goals:** progress visible without asking; a way back to an unfinished form from anywhere.

**Non-Goals:** formguide does not store form values as a draft (the config stays the form backend's); no cross-device drafts beyond what the host's `drafts` callback gives.

## Decisions

- **The draft is a pointer, not data.** Formguide keeps title, counts, path and time only; reopening the page reloads the real values from the form backend. Alternative: store the last config; rejected, it breaks "the config is the source of truth".
- **Progress from the existing counter.** The event reuses the numbers of the form context, so the header and the model never disagree.
- **Host override.** A host with real saved drafts passes `drafts=fn(ctx)`; formguide's pointers are the fallback for hosts that keep the form state in the browser session.
- **One offer per page.** Dushes offers to continue through `suggestions`, at most once per page, so it never nags.

## Risks / Trade-offs

- [A pointer to a form whose values the host already dropped] → the form page shows its real state; the agent reads the fresh config on the first turn and says what is left.
- [Progress counts change when the form reveals fields] → the header shows the current count; it may go from 12 of 30 to 12 of 36, which is honest.

# Proposal

## Why

A long form gives no sense of how far the user is, and once they leave its page the chat forgets the application exists: there is no "Continue the application" anywhere. The agent already counts required fields; it should show that progress and bring the user back to an unfinished form from any page.

## What Changes

- After every form turn the run emits CUSTOM `progress {form_id, title, filled, required, section?}`; the widget shows "Application · 12 of 36" in its header.
- Formguide keeps a draft record per site thread and form (title, progress, page path, last activity), updated from the form's turns, and returns it from `GET /site/threads/{id}` as `drafts`.
- A host MAY supply `drafts=fn(ctx)` to list its own saved drafts (a real draft lives in the form backend); formguide's record is used when it does not.
- On a page without that form, Dushes knows the unfinished drafts: it offers "Continue the application" as a suggestion, and `open_form` to a draft form carries no note but "continue where they left off".
- A finished form (submitted through `review_form` or reported by the host) drops its draft.

## Capabilities

### New Capabilities
- `form-progress`: progress of a form in the chat and unfinished forms the user can return to.

### Modified Capabilities
- `dushes`: Dushes knows the user's unfinished forms and offers to continue them.

## Impact

- Backend: `backend/formguide/guide.py` (the progress event), `backend/formguide/site/guide.py` (draft records, `drafts` callback, the threads endpoint), `site/agent.py` (drafts in the prompt).
- Widget: the header progress line in `packages/agui-chat` (coordinate with the UX/UI session).
- Demo: `frontend/src/site/Site.tsx`.
- Docs: `backend/dushes.mdx`, `frontend/dushes.mdx`, `reference/agui-events.md`, `reference/http-api.md`, the card gallery if the header changes.

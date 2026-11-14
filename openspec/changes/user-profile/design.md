# Design

## Context

Today a user's values live only in the form config and in each thread's transcript. `memory:` compacts long chats; it knows nothing about who the user is. Domain packs already mark `pii` fields by name, which the context renders as `<filled>`. Prefill (`forwardedProps.prefill`) already turns data into a confirmation card.

## Goals / Non-Goals

**Goals:**
- Everything configurable in `formguide.yaml`; the core stays domain-agnostic through the pack's mapping.
- Values come back only through a card, like any other change.

**Non-Goals:**
- No learning of preferences or free-text facts ("prefers mornings"); only configured keys.
- No cross-host sharing; one store per formguide deployment.
- No authentication: the host vouches for the user id.

## Decisions

- **Key-value profile, not a memory model.** A profile is `{user_id: {key: {value, saved_at}, consent}}`. Alternative: an LLM summary of the person; rejected, it cannot be checked, expired or forgotten key by key.
- **Mapping in the pack.** `profile: {field: key}` per form keeps loans and bookings apart in configuration only, the same principle as glossary and `pii`.
- **The offer reuses prefill.** On a thread's first run with a profile, the mapped values become `prefill.data` with a "from last time" note, so the agent proposes them in its usual card. Alternative: a new card type; rejected, the existing card already has Undo and partial accept.
- **Saving at the confirm node.** The graph already knows exactly which rows the user kept (`names`, `edited`); the save hooks there, so rejected and edited values are handled correctly.
- **Consent as a confirm card.** `consent: ask` uses `confirm_action`'s card with the keys listed; the answer is stored in the profile.
- **Storage.** A JSON file per user id hash under `data_dir/profiles/` by default; a host callback `store: module:function` for a database. User ids are hashed in file names and logs.
- **User id.** `user_id: header:X-User-Id` (default) or `forwarded:user_id`; `create_router(..., user_id=fn)` for code.

## Risks / Trade-offs

- [Wrong user id from the host shows one person's data to another] → the docs state the host owns authentication; ids come only from server-side configuration, never from the model.
- [Stale values] → `keep_for` expiry and the card shows the value before it is applied.
- [Personal data at rest] → off by default, hashed file names, `DELETE` endpoint, `keep_for`; the docs list what is stored.

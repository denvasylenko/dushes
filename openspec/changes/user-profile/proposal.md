# Proposal

## Why

Every form and every new chat asks the same person for the same name, phone, email and address again. Hosts know who the user is, so Dushes and the form agent can remember these values across forms and conversations, when the business turns it on and the user agrees, and offer them back with one tap instead of a retyped answer.

## What Changes

- A `profile:` section in `formguide.yaml` (and `FormGuide(profile=...)`): on or off, which profile keys exist, where the user id comes from, the consent mode, how long values are kept and where they are stored.
- Domain packs map their fields to profile keys (`profile: {first_name: name, mobile: phone}`), so the core stays domain-agnostic.
- Remembering: after the user accepts a card, accepted values of mapped fields are saved for that user id; with `consent: ask` the first save asks once with a card.
- Offering back: on a form with mapped empty fields, the agent proposes the profile's values in one confirmation card ("Use your details from last time?"); nothing is filled without the card.
- Dushes may use the profile's name in its replies and pass profile values into an `open_form` hand-off.
- Forgetting: the user can say "forget my details"; `DELETE /profile/{user_id}` removes everything for the host.
- The profile is not the conversation memory: the existing `memory:` (compaction of long chats) is unchanged.

## Capabilities

### New Capabilities
- `user-profile`: remembering a user's own details across forms and chats: configuration, consent, saving accepted values, offering them back, forgetting.

### Modified Capabilities
- `domain-packs`: a pack may map its fields to profile keys.

## Impact

- Backend: `backend/formguide/config.py` (the `profile` section), a new `backend/formguide/profile.py` (storage under `data_dir/profiles/` or a host callback), `agent/graph.py` (save after an accepted card, the offer on a new thread), `domain/packs.py` (the `profile` map), `server.py` (user id, the delete endpoint), `site/` (Dushes reads the name, hand-off carries values).
- Demo: `backend/demo/formguide.yaml`, the loan and booking packs.
- Docs: a new `backend/profile.mdx`, `backend/configuration.mdx`, `reference/configuration.md`, `reference/http-api.md`, `backend/domain-packs.mdx`, `concepts/memory.mdx`, README.
- Off by default: no behaviour changes without `profile.enabled`.

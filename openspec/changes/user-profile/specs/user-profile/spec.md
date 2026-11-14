# Spec Delta

## Purpose
Remember a user's own details (name, phone, email, address and other configured keys) across forms and conversations, only when the business enables it and the user agrees, and offer them back through a confirmation card.

## ADDED Requirements

### Requirement: Configured in one place
`formguide.yaml` SHALL accept `profile: {enabled, keys, user_id, consent, keep_for, store}` (keys kept, user id source, consent mode, expiry, storage). With `enabled: false` (default) or no user id in a run, nothing SHALL be saved or offered.

#### Scenario: Off by default
- **WHEN** the config has no `profile` section and the user accepts a card with their phone
- **THEN** nothing is saved for any user

#### Scenario: No user id
- **WHEN** the profile is enabled but the run carries no user id
- **THEN** the run works as without a profile

### Requirement: Profile options
`user_id` SHALL be `header:<name>`, `forwarded:<key>` or a host callback; `consent` SHALL be `ask` (default), `always` or `never`; `keep_for` SHALL default to `365d`; `store` SHALL be a folder under `data_dir` or a host storage callback.

#### Scenario: A user id from a header
- **WHEN** `user_id: header:X-User-Id` and a run carries `X-User-Id: u42`
- **THEN** values are saved and offered for `u42`

### Requirement: Saving accepted values
After the user accepts a field-change card, the accepted values of fields that the form's domain pack maps to a configured key SHALL be saved under the run's user id, with the time saved. Values the user did not accept, values the agent only proposed and fields without a mapping SHALL NOT be saved.

#### Scenario: A phone on the loan form
- **WHEN** the loan pack maps `mobile` to `phone` and the user accepts a card setting `mobile`
- **THEN** the profile of that user holds `phone` with that value

#### Scenario: A rejected card
- **WHEN** the user rejects a card with their email
- **THEN** the profile is unchanged

### Requirement: Consent
With `consent: ask`, the first save for a user SHALL be preceded by a confirmation card naming the keys to be kept; a refusal SHALL be remembered and nothing SHALL be saved for that user until they ask for it. With `consent: always` values SHALL be saved without asking (the host has the user's consent); with `never` the profile SHALL only be read, never written.

#### Scenario: Asked once
- **WHEN** a user accepts their first card with a mapped field under `consent: ask`
- **THEN** a card asks whether to remember name and phone, and the values are saved only after yes

### Requirement: Offering the values back
On a form with empty editable fields mapped to keys the profile holds, the agent SHALL propose those values in one field-change card, saying they are from last time; the values SHALL reach the form only through that card. Expired values SHALL NOT be offered.

#### Scenario: A second form
- **WHEN** a user whose profile holds name and phone opens the booking form for the first time
- **THEN** the agent's first card proposes the booking form's name and phone fields with those values

### Requirement: Dushes knows the person
Dushes SHALL see the profile's keys and values in its turn and MAY address the user by name; an `open_form` hand-off SHALL include the profile values that the target form maps.

#### Scenario: A greeting by name
- **WHEN** a user with `name: Anna` writes "hi" on the home page
- **THEN** the reply may call her Anna

### Requirement: Forgetting
A user message asking to forget their details SHALL remove their profile after a confirmation card, and `DELETE /profile/{user_id}` SHALL remove it for the host. A removed profile SHALL NOT be offered again.

#### Scenario: Forget me
- **WHEN** the user writes "forget my details" and confirms
- **THEN** the profile is removed and the next form offers nothing from it

# Design

## Mini-brief (ui-craft)
1. **Who and why:** a person fills a long form with the assistant, often on a phone.
2. **Main action:** each card keeps one filled button or one tap that answers.
3. **Tap ladder:** date typed in a picker (3 taps) -> one tap on a day; term with payment shown elsewhere (type, ask, card) -> drag and "Set 5 years"; first and last name over 4 turns -> one card; a 214-bank list -> type 2 letters.
4. **States:** a missing payload key or host callback falls back to today's control; apply errors keep the card with a readable error; Undo after every fill; restored cards render the same.
5. **Phone:** comparison columns stack; actions stick to the bottom of a long card; the camera button comes first; targets 44 px.

## Consistency
Every variant reuses the existing classes: `.card`, `.card-q`, `.card-t`, `.chips/.chip`, `.row`, `.acts`, `.btn pri|sec|link`, `.ok-line`, `.muted`, tokens only. New classes are small additions in one block of `styles.ts`: `.opt` (an option with a second line), `.cmp` (comparison grid), `.strip` (day strip), `.range`, `.issue`, `.src`, `.rev`.

## Payloads
As proposed to Owner (see the session notes): `kind`, card `reason`, `consent`, `doc`, `issue`, card `source`, `confidence`; options `description`, `attrs`, `suggested`; `input` types date, time, number range, address; `slots`; `fields`; interrupt `review`; CUSTOM `sources` and `receipt`; confirm `details`, `consequence`; request_file `privacy`.

## Host callbacks
`preview(field, value)`, `getSlots(field, date)`, `lookupAddress(field, query)`, `onFeedback(value)`, all optional.

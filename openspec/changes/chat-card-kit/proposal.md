# Proposal

## Why

The chat's cards cover four interactions (field changes, questions, file requests, confirmations) with one look each. In a live session one decision still cost several taps or turns: a date typed into a picker, a term chosen without seeing the payment, a name asked field by field, a long bank list impossible to scan, a final check done in prose. The user reviewed 20 card ideas in a gallery and picked all 17 merged cards.

The constraint: the model must not get more tools. It decides what to ask; the widget decides how to draw it from the data it already gets (field type, range, option count, descriptions). Only `review_form` is new, and it is the backend's (Owner's) change.

## What Changes

The widget renders richer variants of the existing cards when the payload carries the data for them, and falls back to today's look when it does not:
- **Field card** (A, 6, 9, 10): values formatted by field `kind` (dates in the locale, ids never digit-grouped), one card-level reason, larger tap targets and sticky actions on phones; consent rows the user must tick, with Read; an inline issue with fix chips and Why; a document header with "check" marks for low-confidence values.
- **Question card** (1-5, 14, 15): options with a description line; a comparison of 2-3 options with attributes; search above 12 options with suggested ones first; a day strip for dates; time slots from the payload or a host callback; a slider or stepper for a number range with a live preview from a host callback; address suggestions from a host callback; several short fields in one card.
- **Review card** (7, 8): form status by section with Continue; the check before sending with Fix (with Undo), Show and Why.
- **Sources** (11): chips under an answer.
- **Confirm and receipt** (12, 16): details and one consequence line; the card turns into a receipt with Copy number; a thumbs rating.
- **Upload** (13): Take a photo first on touch screens, and a privacy line.
- The plugin announces what it renders: `forwardedProps.capabilities`.

## Capabilities

### Modified Capabilities
- `chat-widget-formguide`: the card variants above, host callbacks, capabilities.

## Impact

- Widget: `src/formguide/pickers.ts` (new), `cards.ts`, `index.ts`, `styles.ts` (one appended block), i18n in seven languages, tests.
- Depends on the backend (Owner) for the new payload keys and `review_form`; every variant is optional.
- Docs: `site/` frontend cards pages, the landing demo script, the ui-craft audit.

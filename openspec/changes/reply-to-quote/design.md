# Design

## Context

The answer's text lives in `.msg.ai > .body` inside the widget's shadow root. Cards, tool steps and the action bar are separate elements in the log. `send()` builds the user bubble and calls `_run({})`, and `_run` merges `forwardedProps` into the input. Dictation starts with `_toggleMic()`.

## Mini-brief

1. **Who:** a site visitor or a cabinet owner reading a long answer who wants to ask about one line.
2. **Main action:** Reply (the capsule's first button).
3. **Steps:** today, copy the line, paste it and write the question (about 4 actions). After this, select the line, tap Reply and type (2).
4. **States:**
   - no mic available: the capsule shows Reply only;
   - selection across two messages, or in a card or the user's own message: no capsule;
   - a quote longer than 300 characters is cut with "…";
   - the quoted message is no longer in the log: the quote shows, and a tap does nothing;
   - an old server ignores the field.
5. **Phone:** the capsule goes under the selection. Swiping right replies to the whole message. The quote bar sits above the field, under the thumb.

## Decisions

- **Reading the selection.**
  - Chrome: `ShadowRoot.getSelection()`.
  - Safari: `Selection.getComposedRanges({ shadowRoots: [root] })`.
  - Others: `document.getSelection()`.
  - The capsule is shown on `selectionchange` after 150 ms, and hidden on an empty selection, a scroll, Esc or a tap elsewhere.
- **The capsule keeps the selection alive.** Its buttons cancel `pointerdown`, so the selection stays until Reply reads it.
- **Above or under the selection.** On a coarse pointer it goes under the selection, because iOS and Android draw their own menu above. Otherwise it goes above, flipping under when there is no room.
- **Where `reply_to` travels.** It goes in `forwardedProps` for that one run, not in `messages[]`: AG-UI messages are schema-checked, and forwardedProps is the extension point. Restored messages lose their `reply_to` before they are sent back as history.
- **Swipe.** A leftward touch drag on `.msg.ai` follows the finger with resistance, up to 64 px. A reply icon fades in at the right, and the reply fires past 56 px. Drags that start in cards, code, tables or images are left alone, and vertical scrolling wins when the drag starts vertical.
- **The jump to the quoted message** uses `scrollIntoView({ block: 'center' })` and a 1.2 s highlight. It is instant when reduced motion is on.

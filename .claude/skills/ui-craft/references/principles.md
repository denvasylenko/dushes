# The ten laws in detail

For each law: the idea, how the references do it, what we already do well, where we break it, and the rule to check.

## 1. One main action

**Idea.** The eye must find what to do at once. Two filled buttons means none.
**References.** Revolut: one big "Send" on the transfer card. Apple Settings: a property changes right in its row.
**We do well.** The field-change card has one filled "Fill in", with "Reject" grey and "Edit"/"Show" as links.
**We break it.** The composer's send button is filled even while the field is empty (it only looks disabled by opacity). A pending card and the composer compete: both look primary.
**Rule.** At most one filled button in view. Hierarchy: filled (`.btn.pri`) → grey (`.btn.sec`) → link (`.btn.link`) → hidden under "More".

## 2. Complex → one tap

**Idea.** People think in intents ("I want a car loan"), not in steps ("open the Loan tab → find Loan type → open the list → pick → confirm"). Glue the steps into one *intent button*.
**References.** Revolut "Split bill": one button, the amounts calculated. Telegram "Forward": pick a chat and that is all.
**We do well.** A field-change card fills several fields in one tap; prefill turns a profile into one card; the agent opens the right tab itself.
**We break it.** A question tied to a field ("What type of loan?" → "Car loan") is followed by a second card that asks to confirm the same value: two taps, no decision in the second.
**Rule.** Write down the tap ladder. Every step where the person makes no decision (only "next" or "confirm what I just said") goes away. Every decision that has the same answer in 80% of cases becomes a default.

## 3. Do, don't ask

**Idea.** "Are you sure?" teaches people to press "Yes" without reading. Better do it at once and offer "Undo".
**References.** Gmail and Telegram: "Chat deleted · Undo". Apple Mail: swipe to archive, shake to undo.
**We do well.** An applied card shows "✓ Filled in · Undo"; Undo puts the previous values back and tells the agent.
**We break it.** Nothing big today; watch new cards: a confirmation card is only for actions that cannot be undone (`confirm_action`, `confirm_tools`).
**Rule.** Reversible → at once + Undo. Irreversible and affecting others (submitting, cancelling, paying) → a confirm card: a title with the object ("Cancel the booking?"), the consequence in one sentence, a red button with a verb and object ("Cancel booking"), and a plain "Cancel".

## 4. Smart defaults

**Idea.** The best question is the one we did not have to ask.
**References.** Revolut fills in the last recipient and currency. iOS offers the SMS code above the keyboard.
**We do well.** Prefill from what the app knows; the agent reads attachments instead of asking to type; the chat's language follows the page; rows on a card are ticked by default.
**We break it.** The dictation language does not remember the last choice in the widget (the demo keeps its own select).
**Rule.** For every input ask: can we know the answer? If yes, fill it in. If nearly, offer it as a chip.

## 5. Progressive disclosure

**Idea.** The simple on the surface, the complex on request, the dangerous deepest.
**We do well.** Tool steps collapse into "Steps: 3 ›" after the run; quick replies appear only after an answer; old→new is a small struck-through value, not a table.
**Rule.** If an element is needed in fewer than 20% of visits, it is not on the surface. Hidden things are always findable (a link, "More", a collapsed list), and active hidden settings show as chips.

## 6. Instant

**Idea.** Speed is the main feature. The feeling of speed matters more than the real one.
**References.** Telegram sends a message at once (clock → tick). Apple animates at once; the data catches up.
**We do well.** The typewriter shows text as it streams; typing dots appear at once; the answered card changes before the server replies.
**We break it.** After a sleeping server wakes up, the first message waits 5 s with only dots (hosted demo).
**Rule.** A change is visible at once (optimistically), rolled back with a message on error. What the client already has is shown at once; the rest draws in.

## 7. Every state is designed

The states of any screen or card: **ideal · empty (first time / nothing found) · loading · partial · error · no access · too many · offline**.
**We do well.** An empty chat shows a title, an intro and starter chips; an unknown card type shows a fallback with Skip; a run error offers "Try again".
**We break it.** The error line glues the server's raw message: "Something went wrong. HTTP 500: …".
**Rule.** Error = what happened (in human words) + what to do + a button. Empty = what will appear here + one action.

## 8. Words are interface too

See `copy.md`. In short: a verb and an object; the person's language, not the protocol's; numbers with separators and plurals; one concept, one word everywhere.

## 9. Fingers and keyboard

**Phone.** Targets ≥ 44×44; the main action in the bottom third (the composer is already there); sheets slide up from the bottom; respect `env(safe-area-inset-*)`; no hover-only actions.
**Computer.** Number keys pick options on a question card; `Enter` sends; `Shift+Enter` adds a line; `Esc` closes the floating panel; `Tab` order is the reading order.
**We break it.** Icon buttons (send, mic, paperclip, header icons) are 36 px; card links (Edit, Show, Undo) are about 24 px tall on a phone.

## 10. Quiet and system

**Idea.** Beauty = consistency. Fewer values, more order.
**We break it.** The widget uses 12 font sizes (including 11.5, 12.5, 13.5, 14.5, 15.5) and 9 radii (4, 5, 9, 12, 24 among them), and the card renderers have about a dozen inline styles. Scales to converge on: `tokens.md`.
**Rule.** A value not on the scale: first ask why the nearest scale value does not fit.

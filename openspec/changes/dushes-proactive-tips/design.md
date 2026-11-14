# Design

## The opening turn

```python
Dushes(guide, site_map, tips={"per_day": 1, "snooze_days": 7}, cards=[...], tools=[...])
```

The client sends `forwardedProps.opened: true` (no message) when the user opens the chat, at most once per page load. The page does nothing by hand: the client plugin gets an option `opening: true` and, on the first `agui:open` of a page load, calls the existing `chat.run({ forwardedProps })` (a turn with no user bubble). It sends nothing while a turn is running or following after a restore, while a card waits, while the chat is busy, or in hero mode (where opening is the first message). Once a day and the snooze are the server's (the ledger). Dushes runs with an internal note in place of the message: "The user opened the assistant. If one thing is worth doing now, call tip; else say nothing." `tip` is the only way to speak in this run; without a call the run ends with no text (no "Hi, how can I help?").

The ledger lives in the thread's transcript as entries of kind `tip` `{topic, text, day, status: shown | later | done}`, so it survives restarts and reloads and needs no new store. `tip` is refused (and the model told so) when `per_day` tips were already shown today, when the topic was declined less than `snooze_days` ago, or when it was shown today. Topics are short ids the host's instructions define ("unanswered_requests", "add_hours").

With `tips_ledger` the host keeps the journal instead (`seen` before the run, `record` on `tip` and `tip_feedback`), and the transcript entries stay only for the thread's own history. With `tip_candidates` the server asks the host first: an empty list ends the opening run at once, no model call; otherwise only those topics are accepted by `tip`, and the list goes into the note ("worth raising: unanswered_requests, add_hours").

"Not now" is understood by the model, not by matching words: while a tip is `shown` and unanswered, the next turn has `tip_feedback(topic, later)`; Dushes calls it when the user declines (or acts on it), then answers as usual. The widget needs nothing new: the tip comes with `suggestions` (the action and "Not now").

## How the tip looks (from the UX/UI review)

An ordinary assistant message with two chips, never a banner (in iOS a banner is a notification outside the app; inside a conversation Apple puts suggestions in the content). One sentence; the action chip is a verb with its object ("Reply to Anna", not "Do it"). Nothing to say: no message and no typing dots. In bubble mode no unread dot and no bounce: the tip only comes once the chat is open. If the tip takes longer than about 2 s, show nothing rather than keep dots on opening.

## Cards

The form agent's `CardSpec` (formguide/cards.py) is reused as is. For Dushes only `wait: false` specs are allowed in this change (a display card goes out as CUSTOM `card` and the turn goes on, as for the form agent); a spec with `wait: true` is refused at start-up with a clear error. The demo gets a `reply_draft` spec as the example, laid out as iOS does it: `title` "Reply to Anna" with where the message came from as the subtitle; `text` with `style: quote` (a soft bubble, so the draft reads as a message; a new variant of the existing text block); `links` share (the system share sheet, which already holds WhatsApp and Messages), copy (confirms "Copied" in place) and, only when WhatsApp should be its own row, web to `https://wa.me/?text=…`; `note` with the source. Not `buttons` for copying: links act at once. Display cards are written to the transcript as kind `display`, so a reply draft survives a reload, as the form agent's do.

## Sources

`SiteTool.handler` may return a dict `{text, sources}`; the model gets `text`, the run collects `sources` and sends them once, before `RUN_FINISHED`, like the form agent's documents. The prompt rule: "a recommendation names where it comes from (a number from the tools, a rule, a document) or says it is general practice".

## Mini-brief (ui-craft), for the page

1. Who: a business owner opening their cabinet's assistant. 2. Main action: the tip's one action (a suggestion chip). 3. Taps: open the chat, tap the action: one. 4. States: nothing worth saying (silence), a tip, declined (quiet), the daily limit. 5. Phone: the tip is one or two lines with two chips under the thumb.

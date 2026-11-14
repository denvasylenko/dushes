# Proposal

## Why

A long answer often has one line the user wants to ask about. Today they retype it or write "the second point". Selecting the line and tapping Reply, as in Claude's chat or Telegram, puts that exact text in front of the agent and in front of the user's own message. The owner wants it in every Dushes chat: the cabinet, client sites and the docs.

## What Changes

- **Selection menu.** Selecting text in an agent's message shows a small capsule above the selection, like the iOS edit menu, with Reply and a microphone. On touch screens it goes under the selection, so it does not cover the system's own selection menu. There is no capsule for the user's own messages, cards or tool steps.
- **Reply.** Reply puts a quote bar at the top of the composer and focuses the field. The bar holds a reply icon, the quote on one line with "…", and a close button. The microphone does the same and starts dictation at once.
- **Removing the quote.** The close button or Esc removes it, with no Undo.
- **Swipe to reply.** On a phone, swiping right on an agent's message replies to the whole message, as in Telegram.
- **Sending.** The run carries `forwardedProps.reply_to = {message_id, quote}`, the quote being plain text of at most 300 characters. The user's bubble shows the quote above its text. A tap on it scrolls to the quoted message and briefly highlights it.
- **After a reload**, a restored user message with `reply_to` shows its quote again.
- **The `voice` option** (`auto` by default, `browser`, `server`, `off`) chooses how the mic turns speech into text. `auto` uses the browser's own recognition only where it is reliable (Chromium on a computer and Android), and otherwise records for the server. `dictation` stays as the old name. The docs say that Chrome's recognition sends the audio to Google.
- **A new option**, `reply` (default on, attribute `reply="off"`), and the new parts `selection-menu`, `reply` and `message-quote`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `chat-widget`: the `voice` option, the selection menu, the quote bar, the quoted bubble, swipe to reply, `reply_to` in the run and on restored messages.

## Impact

- **Widget:**
  - `packages/agui-chat/src/element.ts`, `styles.ts` and `types.ts`;
  - texts in `i18n.ts` and the 6 language packs;
  - tests in `test/reply.test.ts`.
- **Backend (Owner):** the agent sees the quote before the message, the transcript keeps it, and restore returns it. Agreed shape: `forwardedProps.reply_to`, with `reply_to` on the restored user message. Old servers ignore the field.
- **Docs:**
  - `frontend/chat-widget.mdx`: the Reply section;
  - `reference/agui-chat.md`: the `reply` option and the new parts;
  - `reference/agui-events.md`: `forwardedProps.reply_to`.

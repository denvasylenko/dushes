# Tasks

## 1. Widget

- [x] 1.1 Selection capsule on agent messages: Reply and the mic, above the selection (under it on touch), hidden on scroll, Esc or an empty selection
- [x] 1.2 Quote bar in the composer: icon, one-line quote, close button, Esc; mic starts dictation
- [x] 1.3 `reply_to` in `forwardedProps` for the run; the quote above the user bubble; a tap scrolls to the message and highlights it
- [x] 1.4 Restore: `reply_to` on user messages drawn, and stripped from the history sent back
- [x] 1.5 Swipe left on an agent message on touch replies to the whole message
- [x] 1.6 Option `reply` and attribute `reply`; parts `selection-menu`, `reply` and `message-quote`
- [x] 1.7 Texts (reply, replyVoice, cancelReply, toQuoted) in English and the 6 packs
- [x] 1.8 Tests in `test/reply.test.ts`
- [x] 1.9 `voice` option (auto, browser, server, off) with reliable-browser detection; `dictation` kept as the old name

- [x] 1.10 A reply to the whole answer as `{message_id, whole: true}`; `voice: auto` prefers the server when the restore says `transcription: true` or `transcribeUrl` is set
- [x] 1.11 Long messages fold (`collapseLines`, `collapseAnswers`), with Show more and Show less, `aria-expanded` and the part `fold-toggle`

## 2. Docs

- [x] 2.1 `frontend/chat-widget.mdx` Reply section; `reference/agui-chat.md` option and parts; `reference/agui-events.md` `forwardedProps.reply_to`

## 3. Check

- [x] 3.1 Browser at 390 px and desktop, light and dark; `ux-review` and `ui-review`
- [x] 3.2 `openspec validate --all --strict`, `check_english`, widget tests, backend pytest, site build

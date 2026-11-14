---
title: '<agui-chat> API'
description: 'Every option (attribute and property), event and method of the chat widget.'
---

The element is configured by attributes, by the `options` property or by props of the React wrapper; plugins add renderers, tools and strings. How to install it and what each part looks like: [The chat widget](../../frontend/widget/).

## Options

Every option can be set in three ways, and changes take effect immediately:

```html
<agui-chat mode="inline" typing="plain" tool-steps="off"></agui-chat>   <!-- attributes -->
```
```js
chat.options = { mode: 'inline', typing: 'plain', toolSteps: false }       // or an object (merged)
```
```jsx
<AguiChat mode="inline" typing="plain" toolSteps={false} />                // or React props
```

| Option (attribute) | Default | What it does |
|---|---|---|
| `url` | `/agent/run` | the AG-UI run endpoint (POST, server-sent events) |
| `threadId` (`thread-id`) | a new id, kept per page | the conversation; the same id brings the chat back after a reload |
| `persistThread` (`persist-thread`) | `true` | keep the thread id in localStorage |
| `mode` | `floating` | `bubble`: a round launcher that grows into a chat window (a bottom sheet on phones); `floating`: a button and a side panel; `inline`: fills its box; `page`: the whole window; `hero`: only the field until the first message, then the chat grows in place (a full-screen sheet on a phone) |
| `bubbleSide`, `greeting`, `greetingDelay`, `motion` | `right`, —, `4`, `spring` | bubble mode: the launcher's corner, a greeting speech bubble and its delay, the opening motion (`spring`, `gentle`, `none`) |
| `open` | `false` | open the floating panel on load |
| `typing` | `words` | `words`: typewriter with words fading in; `plain`: text as it arrives; `off`: the whole message at the end |
| `typingSpeed` | `55` | characters per second at least (it speeds up when text is waiting) |
| `fadeMs` | `450` | how long a new word takes to fade in |
| `toolSteps` (`tool-steps`) | `true` | the live list of what the agent is doing |
| `toolLabels` | — | `{tool_name: "Label"}` for the step list |
| `mic` | `true` | the dictation button (only where the browser supports speech recognition) |
| `micLang` (`mic-lang`) | the chat's language | the dictation language, e.g. `ru-RU`, `en-GB` |
| `micAutoSend` (`mic-auto-send`) | `false` | send the message as soon as the user stops dictating (hands-free) |
| `voice` (`voice`) | `'auto'` | how speech becomes text: `'auto'` (the server when it transcribes: its restore returns `transcription: true`, or `transcribeUrl` is set; without one, the browser's own recognition where it is reliable, Chromium on a computer and on Android, and elsewhere a recording posted to `transcribeUrl`), `'browser'` (the browser only; no mic where it has none), `'server'` (always record: a wave and a timer in place of the input, then "Transcribing…", then the text in the input to check and send), `'off'` (no mic). Chrome's recognition sends the audio to Google, so sites with sensitive data should use `'server'` |
| `dictation` (`dictation`) | `''` | deprecated, the old name of `voice` (`'browser'`, `'server'`, `'auto'`); used when `voice` is left at `'auto'` |
| `transcribeUrl` (`transcribe-url`) | `transcribe` next to `url` | where recordings go (`/agent/run` → `/agent/transcribe`); through the chat's connection (`headers`, `fetch`, `request` with kind `transcribe`) |
| `attach` | `true` | the paperclip (only when files can be uploaded: the `upload` option or a plugin, e.g. Dushes) |
| `attachAccept` (`attach-accept`) | the plugin's types | file types offered, e.g. `.pdf,.jpg` |
| `attachMultiple` (`attach-multiple`) | `true` | several files at once |
| `attachMaxMb` (`attach-max-mb`) | `20` | the largest file; bigger ones are refused with a message |
| `imageMaxPx` (`image-max-px`) | `2000` | photos larger than this (or 1.5 MB) are shrunk to a JPEG before upload; `0` sends them as they are |
| `upload` | the plugin's | your own uploader: `(file, chat) => Promise<{id, filename}>` (attachments without Dushes) |
| `quickReplies` (`quick-replies`) | `true` | starter chips in an empty chat and suggested replies after answers |
| `starters` | — | opening messages for an empty chat (Dushes also reads them from the domain pack) |
| `title`, `subtitle`, `intro`, `placeholder` | localized defaults | the header, the empty-chat text, the composer hint |
| `launcher` | `auto` | the launcher in every popup mode: `auto` (a pill with its words for the panel, a round button for the bubble), `round`, `pill`, `none` (your own button calls `chat.open()`); `render.launcher` replaces its content in any of them |
| `launcherLabel` | the language's "Open" | the launcher's words ("Edit with AI") and its accessible name |
| `modal` | `true` | floating panel: `false` (`modal="off"`) keeps the page beside it usable, like a sidebar next to the site it talks about: no scrim, a tap on the page does not close it, no focus trap; on a phone it is still a sheet |
| `reply` (`reply`) | `true` | Reply to a part of an answer, as in the Claude app: a selection in an agent message shows a Reply capsule, which opens a reply window (the quote, a field "Reply to …", a mic, Add to chat; one dictation at a time); Enter or Add to chat puts the quote (with what was typed as its reply) as a tile into the composer, under the others, several in one message. The run carries `forwardedProps.reply_to [{message_id, quote | whole, note?}]`; the bubble shows every quote and its reply, and a tap scrolls to the answer. Reply under an answer, or a swipe left on a phone, quotes the whole answer. Parts: `selection-menu`, `reply-window`, `reply`, `reply-quote`, `message-quote` |
| `shortcutHints` (`shortcut-hints`) | `true` | tooltips with keyboard shortcuts on the composer's buttons, after ~500 ms of hover or at once on keyboard focus, never on a touch screen: Send (Enter) and New line (Shift+Enter), Dictate (Cmd/Ctrl+D), Attach, and Add to chat (Enter) in the reply window. Keys show as ⌘ ⌥ ⇧ ↵ on a Mac and as words elsewhere. Part `tooltip`. The tooltip loads on the first hover or focus (its own chunk with a bundler, `agui-chat.tip.js` next to the one-script build); `keyLabel`, `ariaKeys` and `isMac` are exported |
| `composerShadow` (`composer-shadow`) | `'soft'` | the composer's shadow: `'soft'` (a little lift, more when focused, fainter in dark), `'raised'`, `'none'`; tokens `--agui-composer-shadow`, `--agui-composer-shadow-focus` |
| `collapseLines` (`collapse-lines`) | `8` | a message taller than this many lines folds: its start fading out and Show more / Show less (`aria-expanded`; part `fold-toggle`); `0`: never |
| `collapseAnswers` (`collapse-answers`) | `false` | fold the assistant's long answers too (off, so an answer is never hidden) |
| `messageActions` | `['copy', 'reply']` | the actions under an answer, in order: `copy`, `reply` (quote the whole answer in the composer; hidden with `reply: false`), `retry` (the latest answer), `speak`, `like`, `dislike`, or your own `{id, label, icon?, hint?}` (icon: an SVG path on a 24 grid; label and hint are the tooltip). `[]` or `message-actions="off"`: none |
| `onMessageAction` | — | `(id, {messageId, text, pressed?}) => true?`: a tap on an action; return `true` to skip the built-in behaviour |
| `footnote` | none | a line under the composer ("The assistant can make mistakes"); a hint or an error takes its place while shown |
| `lang` | the page's `lang` | UI language: `en` (built in), `ru`, `uk`, `de`, `fr`, `it`, `es` (packs loaded on first use, English until then; your own with `addLanguage`); also used for dictation |
| `i18n` | — | override any UI string: `{ send: "Go" }` |
| `theme` | `default` | a theme name (`default`; the packs `glass`, `bold`, `messenger`, `contrast`, loaded on first use; or one from `defineTheme`) or a theme object; see [Themes](../../frontend/themes/#themes). `auto`, `light` and `dark` still work and set the scheme |
| `scheme` | `auto` | `auto` (follows the system, also when it changes), `light`, `dark` |
| `icons` | — | replace built-in icons: `{logo, send, stop, mic, clip, plus, close}`, each an SVG string or an element; see [Themes](../../frontend/themes/#icons) |
| `render` | — | your own components in place of pieces: `{markdown, assistant, user, empty, header, error, suggestions, sources, composer}`; see [Themes](../../frontend/themes/#your-own-components-slots) |
| `cards` | — | feature flags per card type, e.g. `{ set_fields: { edit: false } }` |
| `resumeStyle` (`resume-style`) | `command` | how a card answer is sent: `forwardedProps.command.resume` (CopilotKit, ag-ui-langgraph) or AG-UI 1.0 `resume[]` |
| `history` | `full` | send the whole conversation each run (AG-UI default) or `last` (only the new messages; Dushes keeps history on the server either way) |
| `headers` | — | request headers: an object, or `({kind, url}) => headers` (sync or async) called before every request |
| `credentials` | — | `fetch` credentials for every request (`include`, `same-origin`, `omit`) |
| `fetch` | global `fetch` | your fetch-compatible function, used for every request |
| `request` | — | `({kind, url, init}) => {url, init}`: change any request last; `kind` is `run`, `attachments`, `thread` or `feedback` |
| `transport` | HTTP | `(input, {signal, chat}) => AsyncIterable<AguiEvent>`: runs without HTTP; takes precedence over `agent` and `url` |
| `forwardedProps`, `state` | — | sent with every run (the form plugin fills `state` for you) |

Unknown option names are ignored with a console warning.

---

## Events and methods

| | |
|---|---|
| `chat.send(text)` | send a message as the user |
| `chat.request(kind, url, init)` | a request through the chat's connection (headers, credentials, fetch, request hook); for plugins and host code |
| `chat.run({ forwardedProps, notice })` | run without a message (e.g. prefill: `{ prefill: { data } }`) |
| `chat.open()`, `chat.close()`, `chat.toggle()` | the floating panel or the bubble |
| `await chat.showCard(payload)` | shows any card without the agent and resolves with the user's answer; see [Calling components](../../frontend/cards/#calling-components-from-your-code) |
| `chat.reset()` | a new conversation (new thread id) |
| `chat.setPlaceholder(text)` | change the composer's hint (a language switch) |
| `agui:open`, `agui:close` | the chat opened or closed (bubble, drawer, hero) |
| `chat.removeMessage(id)` | take back an assistant message already shown (and from the history) |
| `chat.updateCard(id, patch)` | redraw a shown card in place: `{blocks}` for a card from blocks |
| `agui:message-action` | an action under an answer was tapped: `{id, messageId, text, pressed?}` (`pressed` for like, dislike, speak) |
| `agui:applied` | the plugin filled fields: `{fields, values, undo}` (also after Undo) |
| `chat.stop()` | abort the running turn |
| `chat.use(plugin)`, `chat.plugins = [...]` | add plugins |
| `chat.registerTool(tool)`, `chat.renderers.set(type, fn)` | frontend tools, card renderers |
| `chat.agent = new HttpAgent(...)` | run through any AG-UI agent object instead of the built-in fetch |
| `blocksCard(payload, ctx, answer, onAction?)`, `loadBlocks()`, `hoursText(value, lang)` | build a card from blocks in a renderer of your own; with the one-script build the blocks come in `agui-chat.blocks.js` on demand (at the first run or the first such card): `blocksCard` returns its element at once and draws into it then, `await loadBlocks()` waits for the file; from `@formguide/agui-chat/formguide` and on `window.AguiChat` ([What loads when](../../frontend/blocks/#what-loads-when)) |
| `loadLanguage(lang)`, `addLanguage(lang, pack)` | load a shipped language pack ahead; register your own (`{core, formguide, tools}`); exported by the package and on `window.AguiChat` |
| `agui:event` | every AG-UI event (`event.detail`) |
| `agui:run-start`, `agui:run-end`, `agui:error` | run lifecycle |
| `agui:thread` | the thread id changed (`event.detail`) |

A plugin is `{ name, renderers?, tools?, toolLabels?, quietSteps?, i18n?, beforeRun?(input, chat), onEvent?(event, chat), onStop?(chat), restore?(threadId, chat), attach? }` (`restore` resolves `{messages, interrupt?, starters?, running?, follow?}`; a message `{id, role: 'activity', activityType: 'card', activity: <card>}` draws a display card again in its place, and is not sent back as history) (`quietSteps`: tools whose steps alone show no step list; `onStop`: the user pressed Stop); `onEvent` returning `true` stops the chat's own handling of that event.



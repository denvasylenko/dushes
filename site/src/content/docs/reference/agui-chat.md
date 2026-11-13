---
title: '<agui-chat> API'
description: 'Every option (attribute and property), event and method of the chat widget.'
---

The element is configured by attributes, by the `options` property or by props of the React wrapper; plugins add renderers, tools and strings. How to install it and what each part looks like: [The chat widget](../../frontend/chat-widget/).

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
| `dictation` (`dictation`) | `'browser'` | who recognises speech: `'browser'` (the browser's own recognition), `'server'` (the chat records and posts to `transcribeUrl`: a wave and a timer in place of the input, then "Transcribing…", then the text in the input to check and send), `'auto'` (the browser where it works, the server where it is missing or blocked) |
| `transcribeUrl` (`transcribe-url`) | `transcribe` next to `url` | where recordings go (`/agent/run` → `/agent/transcribe`); through the chat's connection (`headers`, `fetch`, `request` with kind `transcribe`) |
| `attach` | `true` | the paperclip (only when files can be uploaded: the `upload` option or a plugin, e.g. formguide) |
| `attachAccept` (`attach-accept`) | the plugin's types | file types offered, e.g. `.pdf,.jpg` |
| `attachMultiple` (`attach-multiple`) | `true` | several files at once |
| `attachMaxMb` (`attach-max-mb`) | `20` | the largest file; bigger ones are refused with a message |
| `imageMaxPx` (`image-max-px`) | `2000` | photos larger than this (or 1.5 MB) are shrunk to a JPEG before upload; `0` sends them as they are |
| `upload` | the plugin's | your own uploader: `(file, chat) => Promise<{id, filename}>` (attachments without formguide) |
| `quickReplies` (`quick-replies`) | `true` | starter chips in an empty chat and suggested replies after answers |
| `starters` | — | opening messages for an empty chat (formguide also reads them from the domain pack) |
| `title`, `subtitle`, `intro`, `placeholder` | localized defaults | the header, the empty-chat text, the composer hint |
| `lang` | the page's `lang` | UI language: `en` (built in), `ru`, `uk`, `de`, `fr`, `it`, `es` (packs loaded on first use, English until then; your own with `addLanguage`); also used for dictation |
| `i18n` | — | override any UI string: `{ send: "Go" }` |
| `theme` | `default` | a theme name (`default`; the packs `glass`, `bold`, `messenger`, `contrast`, loaded on first use; or one from `defineTheme`) or a theme object; see [Themes](../../frontend/themes/#themes). `auto`, `light` and `dark` still work and set the scheme |
| `scheme` | `auto` | `auto` (follows the system, also when it changes), `light`, `dark` |
| `icons` | — | replace built-in icons: `{logo, send, stop, mic, clip, plus, close}`, each an SVG string or an element; see [Themes](../../frontend/themes/#icons) |
| `render` | — | your own components in place of pieces: `{markdown, assistant, user, empty, header, error, suggestions, sources, composer}`; see [Themes](../../frontend/themes/#your-own-components-slots) |
| `cards` | — | feature flags per card type, e.g. `{ set_fields: { edit: false } }` |
| `resumeStyle` (`resume-style`) | `command` | how a card answer is sent: `forwardedProps.command.resume` (CopilotKit, ag-ui-langgraph) or AG-UI 1.0 `resume[]` |
| `history` | `full` | send the whole conversation each run (AG-UI default) or `last` (only the new messages; formguide keeps history on the server either way) |
| `headers` | — | request headers: an object, or `({kind, url}) => headers` (sync or async) called before every request |
| `credentials` | — | `fetch` credentials for every request (`include`, `same-origin`, `omit`) |
| `fetch` | global `fetch` | your fetch-compatible function, used for every request |
| `request` | — | `({kind, url, init}) => {url, init}`: change any request last; `kind` is `run`, `attachments`, `thread` or `feedback` |
| `transport` | HTTP | `(input, {signal, chat}) => AsyncIterable<AguiEvent>`: runs without HTTP; takes precedence over `agent` and `url` |
| `forwardedProps`, `state` | — | sent with every run (the formguide plugin fills `state` for you) |

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
| `agui:applied` | the plugin filled fields: `{fields, values, undo}` (also after Undo) |
| `chat.stop()` | abort the running turn |
| `chat.use(plugin)`, `chat.plugins = [...]` | add plugins |
| `chat.registerTool(tool)`, `chat.renderers.set(type, fn)` | frontend tools, card renderers |
| `chat.agent = new HttpAgent(...)` | run through any AG-UI agent object instead of the built-in fetch |
| `loadLanguage(lang)`, `addLanguage(lang, pack)` | load a shipped language pack ahead; register your own (`{core, formguide, tools}`); exported by the package and on `window.AguiChat` |
| `agui:event` | every AG-UI event (`event.detail`) |
| `agui:run-start`, `agui:run-end`, `agui:error` | run lifecycle |
| `agui:thread` | the thread id changed (`event.detail`) |

A plugin is `{ name, renderers?, tools?, toolLabels?, quietSteps?, i18n?, beforeRun?(input, chat), onEvent?(event, chat), onStop?(chat), restore?(threadId, chat), attach? }` (`quietSteps`: tools whose steps alone show no step list; `onStop`: the user pressed Stop); `onEvent` returning `true` stops the chat's own handling of that event.



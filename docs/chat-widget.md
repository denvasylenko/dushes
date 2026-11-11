# The chat widget: `<agui-chat>`

A ready-made chat for any AG-UI agent, as one HTML element. It streams the agent's answer with a smooth typewriter, shows what the agent is doing step by step, renders cards (field changes, questions, file requests, confirmations) and lets the user dictate, attach files and pick suggested replies. Every part can be switched off or restyled.

It is a plain Web Component, so it works on any page: plain HTML, React, Vue, Angular, server-rendered templates. It has no runtime dependencies; the one-script build is about 23 KB gzipped. The look and motion come from the chat of the Cheese project (Herefront AI).

Source: [`packages/agui-chat/`](../packages/agui-chat/). Try it: run the demo server and open http://localhost:8000/examples/widget/ (every setting can be switched live there), or the demo app at http://localhost:8000.

---

## In 30 seconds

```html
<agui-chat url="/agent/run"></agui-chat>
<script src="agui-chat.iife.js"></script>
```

That is a working chat with any AG-UI endpoint: a round button in the corner opens a side panel. For formguide, add the plugin, which sends your form with every message and draws formguide's cards:

```html
<script>
  document.querySelector('agui-chat').use(AguiChat.formguide({
    getState: () => ({ config, jsx_hash, form_id, ui }),     // the form as your backend last built it
    applyChanges: (changes) => myFormBackend.apply(changes),  // returns the new config
  }))
</script>
```

---

## Install

| How | Code |
|---|---|
| One script tag | `<script src=".../agui-chat.iife.js"></script>` defines `<agui-chat>` and `window.AguiChat` (`AguiChat.formguide`, `AguiChat.h`) |
| npm (any bundler) | `import '@formguide/agui-chat'` defines the element; `import { formguide } from '@formguide/agui-chat/formguide'` |
| React | `import { AguiChat } from '@formguide/agui-chat/react'` then `<AguiChat url="/agent/run" plugins={[formguide({...})]} />` |

Build it from this repository: `cd packages/agui-chat && npm install && npm run build` (output in `dist/`; `npm test` runs the tests). The package is not published to npm yet; until then use the built files or `npm pack`.

---

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
| `mode` | `floating` | `floating`: a button and a side panel; `inline`: fills its box; `page`: the whole window |
| `open` | `false` | open the floating panel on load |
| `typing` | `words` | `words`: typewriter with words fading in; `plain`: text as it arrives; `off`: the whole message at the end |
| `typingSpeed` | `55` | characters per second at least (it speeds up when text is waiting) |
| `fadeMs` | `450` | how long a new word takes to fade in |
| `toolSteps` (`tool-steps`) | `true` | the live list of what the agent is doing |
| `toolLabels` | — | `{tool_name: "Label"}` for the step list |
| `mic` | `true` | the dictation button (only where the browser supports speech recognition) |
| `micLang` (`mic-lang`) | the chat's language | the dictation language, e.g. `ru-RU`, `en-GB` |
| `micAutoSend` (`mic-auto-send`) | `false` | send the message as soon as the user stops dictating (hands-free) |
| `attach` | `true` | the paperclip (only when files can be uploaded: the `upload` option or a plugin, e.g. formguide) |
| `attachAccept` (`attach-accept`) | the plugin's types | file types offered, e.g. `.pdf,.jpg` |
| `attachMultiple` (`attach-multiple`) | `true` | several files at once |
| `attachMaxMb` (`attach-max-mb`) | `20` | the largest file; bigger ones are refused with a message |
| `imageMaxPx` (`image-max-px`) | `2000` | photos larger than this (or 1.5 MB) are shrunk to a JPEG before upload; `0` sends them as they are |
| `upload` | the plugin's | your own uploader: `(file, chat) => Promise<{id, filename}>` (attachments without formguide) |
| `quickReplies` (`quick-replies`) | `true` | starter chips in an empty chat and suggested replies after answers |
| `starters` | — | opening messages for an empty chat (formguide also reads them from the domain pack) |
| `title`, `subtitle`, `intro`, `placeholder` | localized defaults | the header, the empty-chat text, the composer hint |
| `lang` | the page's `lang` | UI language: `en`, `ru`, `uk`, `de`, `fr`, `it`, `es`; also used for dictation |
| `i18n` | — | override any UI string: `{ send: "Go" }` |
| `theme` | `auto` | `auto` (follows the system), `light`, `dark` |
| `cards` | — | feature flags per card type, e.g. `{ set_fields: { edit: false } }` |
| `resumeStyle` (`resume-style`) | `command` | how a card answer is sent: `forwardedProps.command.resume` (CopilotKit, ag-ui-langgraph) or AG-UI 1.0 `resume[]` |
| `history` | `full` | send the whole conversation each run (AG-UI default) or `last` (only the new messages; formguide keeps history on the server either way) |
| `headers` | — | extra HTTP headers (e.g. auth) |
| `forwardedProps`, `state` | — | sent with every run (the formguide plugin fills `state` for you) |

Unknown option names are ignored with a console warning.

---

## Look: theme tokens and parts

The widget renders in a shadow root, so your page's CSS does not leak in and its CSS does not leak out. Change the look with CSS custom properties on the element:

```css
agui-chat {
  --agui-accent: #0a7f6f;      /* buttons, the floating button, the logo */
  --agui-on-accent: #fff;
  --agui-radius: 8px;          /* cards and the inline frame */
  --agui-font: "Inter", sans-serif;
  --agui-panel-width: 520px;
}
```

All tokens: `--agui-accent`, `--agui-on-accent`, `--agui-link`, `--agui-bg`, `--agui-surface`, `--agui-soft`, `--agui-ink`, `--agui-ink-2`, `--agui-ink-3`, `--agui-line`, `--agui-line-2`, `--agui-ok`, `--agui-danger`, `--agui-radius`, `--agui-panel-width`, `--agui-font`, `--agui-ease`. The dark theme sets its own values; set yours on `agui-chat.dark` for dark mode.

For deeper changes use parts: `panel`, `header`, `log`, `message`, `user`, `assistant`, `steps`, `card`, `card-<type>`, `chip`, `composer`, `input`, `send`, `fab`, `notice`.

```css
agui-chat::part(card) { border-width: 2px; }
agui-chat::part(fab) { bottom: 90px; }
```

With the system setting "reduce motion", nothing animates.

---

## What the user sees, and where it comes from

| On screen | AG-UI event |
|---|---|
| the answer, typed out | `TEXT_MESSAGE_START/CONTENT/END` |
| three bouncing dots | a run started and no text came yet |
| "Searching the business documents" with a spinner, then a tick | `TOOL_CALL_START` … `TOOL_CALL_RESULT` of a server tool |
| sub-steps under it ("Reading a document") | `CUSTOM tool_progress {parent_id, name}` |
| "Steps: 3 ›" (collapsed after the run) | the same steps, folded when the run ends |
| a card | `CUSTOM on_interrupt` (JSON value with `type`) or `RUN_FINISHED.outcome.interrupts` |
| chips under the answer | `CUSTOM suggestions {items}` |
| "Something went wrong" + Try again | `RUN_ERROR` or a network error |

---

## Cards: the renderer registry

Each interrupt has a `type`. The widget looks up a renderer for it, shows what it returns, and when the renderer calls `resolve(value)`, resumes the same thread with `value` as the answer. Unknown types get a simple card with the payload and *Skip*.

```js
chat.renderers.set('pick_seat', (payload, ctx) => {
  const box = AguiChat.h('div', null, AguiChat.h('div', { class: 'card-q' }, 'Pick a seat'))
  for (const seat of payload.seats) {
    box.append(AguiChat.h('button', { class: 'chip', onclick: () => ctx.resolve({ seat }) }, seat))
  }
  return box
})
```

`ctx` has `resolve(value)`, `t(key)` (the UI strings), `flags` (this type's entry of the `cards` option), `restored` (shown again after a reload) and `chat`. Reusable classes inside cards: `card-t` (small title), `card-q` (question), `chips` + `chip`, `acts`, `btn pri` / `btn sec` / `btn danger` / `btn link`, `ok-line`, `muted`. After `resolve`, buttons in the card are disabled, except ones marked `data-keep`.

---

## Frontend tools

Tools that run in the browser. They are sent as `tools` with each run; when the agent calls one, the widget runs your handler and continues the run with the result.

```js
chat.registerTool({
  name: 'show_map',
  description: 'Show the branch on a map',
  parameters: { type: 'object', properties: { address: { type: 'string' } } },
  label: 'Opening the map',                       // optional: show it in the step list
  handler: async ({ address }, { render }) => {
    render(myMapElement(address))                 // optional: put an element into the chat
    return 'shown'                                // goes back to the agent
  },
})
```

---

## The formguide plugin

```js
import { formguide } from '@formguide/agui-chat/formguide'

chat.use(formguide({
  getState: () => ({ config, jsx_hash, form_id, ui }),   // sent as the run's state
  applyChanges: async (changes) => newConfig,             // your form backend; same path as user input
  revertChanges: async (previous) => {},                  // optional, for Undo (default: applyChanges)
  onDirective: (d) => openTabsAndHighlight(d),            // optional "look here"; default: scroll to [data-name]
  baseUrl: '/agent',                                      // where threads and attachments live (default: url minus /run)
  fieldCard: { select: true, diff: true, reason: true, edit: true, jump: true, undo: true },
  undoSeconds: 20,
  cardSteps: false,                                       // show "Preparing a question" etc. as steps too
}))
```

It does five things:

1. **Sends the form** (`getState()`) as `state` with every run, plus the files attached in the composer.
2. **Applies directives** (`ui_directive`): your `onDirective`, or scrolling to `[data-name=target]` and flashing it.
3. **Draws formguide's cards**:

   | Card | What the user can do | Resume value |
   |---|---|---|
   | `set_fields`: field changes | untick rows, see old → new, edit a value (text, number, date, or another option), jump to the field, Undo after applying | `{accepted, config, ui, names?, edited?}` |
   | `ask`: a question | click an option (or press 1-9), tick several, type an answer, pick a date / time / number | `{answer: {ids?, text?}}`, Skip: `{accepted: false}` |
   | `upload`: a file request | drop a file or choose one; uploads with a progress bar | `{attachment_ids}`, Skip: `{accepted: false}` |
   | `confirm`: a confirmation | Confirm (red when `danger`) or Cancel | `{accepted}` |

4. **Restores the chat** after a reload: `GET {baseUrl}/threads/{id}?format=agui&form_id=…` gives the messages, a pending card and the form's starters.
5. **Labels the steps** of formguide's tools in seven languages ("Looking at the form", "Reading your document", …). The tools that produce a card (`propose_changes`, `ask_user`, `request_file`, `confirm_action`) get no step of their own, since the card shows the result; `cardSteps: true` shows them.

Edited values are applied in the shape the form uses: a dropdown that stores the option object gets the option object, one that stores an id gets the id.

---

## Events and methods

| | |
|---|---|
| `chat.send(text)` | send a message as the user |
| `chat.run({ forwardedProps, notice })` | run without a message (e.g. prefill: `{ prefill: { data } }`) |
| `chat.open()`, `chat.close()` | the floating panel |
| `chat.reset()` | a new conversation (new thread id) |
| `chat.stop()` | abort the running turn |
| `chat.use(plugin)`, `chat.plugins = [...]` | add plugins |
| `chat.registerTool(tool)`, `chat.renderers.set(type, fn)` | frontend tools, card renderers |
| `chat.agent = new HttpAgent(...)` | run through any AG-UI agent object instead of the built-in fetch |
| `agui:event` | every AG-UI event (`event.detail`) |
| `agui:run-start`, `agui:run-end`, `agui:error` | run lifecycle |
| `agui:thread` | the thread id changed (`event.detail`) |

A plugin is `{ name, renderers?, tools?, toolLabels?, i18n?, beforeRun?(input, chat), onEvent?(event, chat), restore?(threadId, chat), attach? }`; `onEvent` returning `true` stops the chat's own handling of that event.

---

## Server side (formguide)

The widget only needs AG-UI. With formguide the server adds:

| Feature | Turn on |
|---|---|
| suggested replies after answers | `suggestions: {enabled: true, max: 3}` in `formguide.yaml` (a cheap model, about 4 s timeout, never blocks the turn) |
| starters for an empty chat | `starters: [...]` in the form's domain pack |
| upload requests, confirmations, date pickers | built in: the agent calls `request_file`, `confirm_action`, `ask_user` with `input` |
| a confirmation before risky tools | `confirm_tools: [submit_application]` |

See [configuration.md](configuration.md) and [ui-components.md](ui-components.md) for the payloads.

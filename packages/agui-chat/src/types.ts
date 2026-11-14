import type { Theme } from './themes'
/** AG-UI wire types the chat uses (a subset of @ag-ui/core, kept local so the package has no dependencies). */

export type Role = 'user' | 'assistant' | 'tool' | 'system' | 'activity'

export interface ToolCall { id: string; type: 'function'; function: { name: string; arguments: string } }

export interface Message {
  id: string
  role: Role
  content?: string
  toolCalls?: ToolCall[]
  toolCallId?: string
  /** role "activity" (AG-UI 1.0): what it is, e.g. "card" (a display card from blocks, content: its payload) */
  activityType?: string
  /** an activity's payload (role "activity") */
  activity?: Record<string, unknown>
  /** a user message that answers part of an earlier agent message (restored from the server; never sent back) */
  reply_to?: ReplyTo | ReplyTo[]
}

/** What the user replies to: a part of an agent's message (`quote`) or all of it (`whole`). */
export interface ReplyTo {
  message_id: string
  /** the quoted plain text of a selection (at most 300 characters) */
  quote?: string
  /** a reply to the whole answer (a swipe or Reply under it): no quote, the server looks the answer up */
  whole?: boolean
  /** the user's own comment on this quote (typed in the reply window, then added to the chat) */
  note?: string
}

export interface ToolSpec { name: string; description: string; parameters?: Record<string, unknown> }

export interface RunAgentInput {
  threadId: string
  runId: string
  messages: Message[]
  state: unknown
  tools: ToolSpec[]
  context: { description: string; value: string }[]
  forwardedProps: Record<string, unknown>
  resume?: { interrupt_id: string; status: 'resolved' | 'cancelled'; payload?: unknown }[]
}

/** Any AG-UI event; `type` is the discriminator (RUN_STARTED, TEXT_MESSAGE_CONTENT, CUSTOM, ...). */
export interface AguiEvent {
  type: string
  [key: string]: any // eslint-disable-line @typescript-eslint/no-explicit-any
}

/** An interrupt as the chat sees it: a `type`, an id to resume, and the rest of the payload. */
export interface Interrupt {
  type: string
  card_id: string
  [key: string]: any // eslint-disable-line @typescript-eslint/no-explicit-any
}

/** What a renderer gets: resolve() sends the user's answer as the resume value. */
export interface RendererContext {
  resolve: (value: unknown, summary?: string) => void
  chat: ChatApi
  t: (key: string, vars?: Record<string, string | number>) => string
  /** This renderer's feature flags from the options (e.g. options.cards.set_fields). */
  flags: Record<string, unknown>
  /** True when shown again after a reload. */
  restored: boolean
}

export type Renderer = (payload: Interrupt, ctx: RendererContext) => HTMLElement

export interface FrontendTool extends ToolSpec {
  /** Runs in the page. The returned value goes back to the agent; `render` may put an element in the chat. */
  handler: (args: any, ctx: { render: (el: HTMLElement) => void; chat: ChatApi }) => unknown | Promise<unknown> // eslint-disable-line @typescript-eslint/no-explicit-any
  /** A label for the step list; frontend tools without one are not shown as steps. */
  label?: string
}

export interface Restored {
  messages?: Message[]
  interrupt?: Interrupt | null
  starters?: string[]
  /** a turn is still running on the server (the page was reloaded mid-answer): the chat checks back until it ends */
  running?: boolean
  /** the running turn's events again (the host's follow stream, from the start of the turn): the chat plays them
   *  as a live run, so the answer goes on word by word after a reload; preferred over `running` */
  follow?: () => AsyncIterable<AguiEvent>
  /** the server transcribes recordings (its `transcription` config): `voice: auto` records for it */
  transcription?: boolean
}

export interface Attachment { id: string; filename: string; [k: string]: unknown }

export interface Plugin {
  name: string
  renderers?: Record<string, Renderer>
  tools?: FrontendTool[]
  toolLabels?: Record<string, Record<string, string> | string>
  i18n?: Record<string, Record<string, string>>
  /** Change the input of every run (e.g. put the form into `state`). */
  beforeRun?: (input: RunAgentInput, chat: ChatApi) => void | Promise<void>
  /** See every event; return true to stop the chat's own handling of it. */
  onEvent?: (ev: AguiEvent, chat: ChatApi) => boolean | void
  /** tools whose steps are routine look-ups: a turn with only these shows no step list (the dots show the wait) */
  quietSteps?: string[]
  /** the user pressed Stop: e.g. tell the server, since a closed connection need not end the turn there */
  onStop?: (chat: ChatApi) => void
  /** Files in the composer: the + button uploads them here; they go with the next message. */
  attach?: { accept?: string; upload: (file: File, chat: ChatApi) => Promise<Attachment> }
  /** Apply a suggestion's field changes (`CUSTOM suggestions` `applies`); return a result line to show, or throw. */
  applySuggestion?: (changes: unknown[], chat: ChatApi) => Promise<HTMLElement | null | void>
  /** Load a saved conversation for a thread id. */
  restore?: (threadId: string, chat: ChatApi) => Promise<Restored | null>
}

/** The part of the element plugins and renderers may use. */
/** Which request the chat is making: `run`, or a plugin's (`attachments`, `thread`, `feedback`, ...). */
export type RequestKind = 'run' | 'attachments' | 'thread' | 'feedback' | 'transcribe' | (string & {})

/** Headers for a request: an object, or a function called before every request (sync or async). */
export type HeadersOption = Record<string, string>
  | ((req: { kind: RequestKind; url: string }) => Record<string, string> | undefined | Promise<Record<string, string> | undefined>)

/** The last word on a request: return the URL and init to send (or nothing to keep them). */
export type RequestHook = (req: { kind: RequestKind; url: string; init: RequestInit }) =>
  { url: string; init: RequestInit } | void | Promise<{ url: string; init: RequestInit } | void>

/** A run without HTTP: the run's input -> AG-UI events (WebSocket, a worker, a mock). */
export type Transport = (input: RunAgentInput, ctx: { signal: AbortSignal; chat: ChatApi }) => AsyncIterable<AguiEvent>

export interface ChatApi {
  readonly threadId: string
  readonly options: ChatOptions
  readonly busy: boolean
  /** The chat's language (two letters), e.g. for plural rules. */
  readonly lang: string
  /** Files attached in the composer for the message being sent (plugins put them into the run). */
  readonly attachments: Attachment[]
  send(text: string): Promise<void>
  /** A request through the chat's connection (headers, credentials, fetch, request hook), for plugins. */
  request(kind: RequestKind, url: string, init?: RequestInit): Promise<Response>
  /** Run the agent without a new message, e.g. run({ forwardedProps: { prefill: {...} } }). */
  run(opts?: { forwardedProps?: Record<string, unknown>; notice?: string }): Promise<void>
  notice(text: string): void
  /** Add an element to the conversation, after the last message. */
  append(el: HTMLElement): void
  /** Change the composer's hint (e.g. on a language switch). */
  setPlaceholder(text: string): void
  /** Replace the suggestions above the composer without a run; `[]` clears them. */
  setSuggestions(items: string[]): void
  /** Take back an assistant message already shown, by its message id. */
  removeMessage(id: string): boolean
  /** Redraw a shown card in place with new data. */
  updateCard(id: string, patch: Record<string, unknown>): boolean
  /** Make a card the host or a plugin drew redrawable by updateCard. */
  registerCard(id: string, payload: Record<string, unknown>, draw: (payload: Record<string, unknown>) => HTMLElement): void
  /** Show any card without the agent; resolves with the user's answer (the value a resume would carry). */
  showCard(payload: Partial<Interrupt> & { type: string }): Promise<unknown>
  /** Run a slot from options.render safely: its element, or null for the default. */
  renderSlot(name: keyof Slots, ...args: unknown[]): HTMLElement | null
  t(key: string, vars?: Record<string, string | number>): string
  host: HTMLElement
}

export interface ChatOptions {
  /** AG-UI run endpoint (POST, SSE). */
  url: string
  threadId?: string
  /** Keep the thread id in localStorage so a reload continues the chat. */
  persistThread: boolean
  /** floating: a side drawer; bubble: a launcher that grows into a chat window; inline: fills its box; page: the whole window. */
  /** hero: only the composer in the page (a landing's big field); the first message grows it into the chat in
   *  place (desktop) or opens a full-screen sheet (phone, under 760 px) */
  mode: 'floating' | 'bubble' | 'inline' | 'page' | 'hero'
  /** bubble mode: the corner of the launcher. */
  bubbleSide: 'right' | 'left'
  /** bubble mode: a short speech bubble next to the closed launcher (once per visitor until closed). */
  greeting: string
  /** Seconds before the greeting appears. */
  greetingDelay: number
  /** spring (a small overshoot), gentle, or none (fades only). */
  motion: 'spring' | 'gentle' | 'none'
  /** words: typewriter + fade-in; plain: text as it arrives; off: text when the message ends. */
  typing: 'words' | 'plain' | 'off'
  toolSteps: boolean
  mic: boolean
  quickReplies: boolean
  /** A registered theme name (see defineTheme) or a theme object. "auto", "light" and "dark" still set the scheme. */
  theme: string | Theme
  /** auto (follows the system, live), light or dark. Empty: from `theme` when it is auto/light/dark, else auto. */
  scheme: '' | 'auto' | 'light' | 'dark'
  lang: string
  title: string
  subtitle: string
  intro: string
  placeholder: string
  /** A line under the composer ("The assistant can make mistakes", "Don't type passwords"); a hint or an error takes
   *  its place while shown. Empty: none. */
  footnote: string
  /** Floating panel: false keeps the page beside it usable (no scrim, a tap on the page does not close it, no focus
   *  trap), like a sidebar next to the site it talks about. On a phone it is still a sheet over the page. Default true. */
  modal: boolean
  /** The launcher in every popup mode: 'auto' (a pill with its label for the panel, a round button for the bubble),
   *  'round', 'pill' (an icon and `launcherLabel`) or 'none' (your own button opens the chat with chat.open()).
   *  render.launcher replaces its content in any of them. Colours come from the theme's accent. */
  launcher: 'auto' | 'round' | 'pill' | 'none'
  /** The launcher's words ("Ask the assistant", "Edit with AI"); default: the language's "Open". */
  launcherLabel: string
  /** The composer's shadow: 'soft' (default; a little lift, a touch more when focused), 'raised' or 'none'.
   *  Exact values: --agui-composer-shadow and --agui-composer-shadow-focus (a theme can set them). */
  composerShadow: 'soft' | 'raised' | 'none'
  /** Tooltips with keyboard shortcuts on the composer's buttons ("Send ↵", "New line ⇧↵"; other buttons show their name), after a moment of hover or
   *  on keyboard focus; never on a touch screen. Default on. */
  shortcutHints: boolean
  /** The actions under an answer, in order: built-in `copy`, `reply` (quotes the whole answer), `retry` (the latest answer), `speak`, `like`, `dislike`,
   *  or your own `{id, label, icon?, hint?}` (icon: an SVG path on a 24 grid). [] or `message-actions="off"`: none.
   *  Default ['copy', 'reply']. Every tap fires `agui:message-action` {id, messageId, text, pressed?}. */
  messageActions: (string | MessageAction)[]
  /** A tap on an action under an answer; return true when you handled it (the built-in behaviour is skipped). */
  onMessageAction?: (id: string, message: { id: string; messageId: string; text: string; pressed?: boolean }) => boolean | void
  /** Reply to a part of an answer: selecting text in an agent's message offers Reply and the mic; on a phone a swipe
   *  left replies to the whole message. The run carries forwardedProps.reply_to {message_id, quote} (or {message_id,
   *  whole: true} for the whole message). Default on. */
  reply: boolean
  /** Long messages fold: a bubble taller than this many lines shows its start, fading out, with Show more under it.
   *  0 turns folding off. Default 8. */
  collapseLines: number
  /** Fold the assistant's long answers too (default off, so an answer is never hidden). */
  collapseAnswers: boolean
  starters: string[]
  /** How to answer an interrupt: forwardedProps.command.resume (CopilotKit, ag-ui-langgraph) or AG-UI 1.0 resume[]. */
  resumeStyle: 'command' | 'resume'
  /** Send the whole conversation each run (AG-UI default) or only the new messages (server keeps history). */
  history: 'full' | 'last'
  /** Headers for every request: an object, or ({kind, url}) => headers (sync or async; e.g. a fresh token). */
  headers: HeadersOption
  /** fetch's credentials for every request, e.g. 'include' for cookies on another domain. */
  credentials?: RequestCredentials
  /** Your fetch (a proxy, retries, logging, tests); default: the global fetch. */
  fetch?: (url: string, init: RequestInit) => Promise<Response>
  /** Change any request last: ({kind, url, init}) => {url, init}. */
  request?: RequestHook
  /** Your own transport for runs instead of HTTP: (input, {signal, chat}) => AG-UI events. */
  transport?: Transport
  forwardedProps: Record<string, unknown>
  state: unknown
  /** Characters per second at least; the reveal speeds up with the backlog. */
  typingSpeed: number
  /** How long a new word takes to fade in, in ms. */
  fadeMs: number
  toolLabels: Record<string, string>
  i18n: Record<string, string>
  /** Per-renderer feature flags, e.g. { set_fields: { edit: false } }. */
  cards: Record<string, Record<string, unknown>>
  /** Open the floating panel on load. */
  open: boolean
  /** Dictation language (BCP 47, e.g. "ru-RU"); empty = the chat's language. */
  micLang: string
  /** Send the message as soon as dictation stops. */
  micAutoSend: boolean
  /** How the mic turns speech into text:
   *  - `auto` (default): the server when it transcribes (its restore says `transcription: true`, or `transcribeUrl`
   *    is set); without one, the browser's own recognition where it is reliable (Chromium on a computer and on
   *    Android), and elsewhere (iPhone, Safari, Firefox) a recording for the server;
   *  - `browser`: the browser only (for sites whose users are on Chrome); no mic where it has none;
   *  - `server`: always record and transcribe on the server;
   *  - `off`: no mic.
   *  Chrome's recognition sends the audio to Google: sites with sensitive data should use `server`. */
  voice: 'auto' | 'browser' | 'server' | 'off'
  /** @deprecated the old name of `voice` (browser, server, auto); used when `voice` is left at `auto`. */
  dictation: '' | 'browser' | 'server' | 'auto'
  /** Where recordings go for `voice: server | auto`; empty = `transcribe` next to `url`. */
  transcribeUrl: string
  /** Show the + button when a plugin (or `upload`) can upload files. */
  attach: boolean
  /** File types the + button offers, e.g. ".pdf,.jpg"; empty = what the plugin accepts. */
  attachAccept: string
  /** Allow several files at once. */
  attachMultiple: boolean
  /** Largest file in MB; bigger files are refused with a message. */
  attachMaxMb: number
  /** Photos larger than this many pixels on a side are shrunk before upload; 0 sends them as they are. */
  imageMaxPx: number
  /** Your own uploader (overrides the plugin's): file -> {id, filename}. */
  upload?: (file: File, chat: ChatApi) => Promise<Attachment>
  /** Replace any built-in icon: an SVG string or an element. */
  icons: Partial<Record<IconName, string | HTMLElement>>
  /** Your own components in place of the chat's pieces; return nothing to keep the default. */
  render: Slots
}

export type IconName = 'logo' | 'send' | 'stop' | 'mic' | 'clip' | 'plus' | 'close'

type Out = HTMLElement | null | undefined | void

/** Slots: each returns the host's element for that piece, or nothing for the default. */
export interface Slots {
  /** The answer's HTML, also while it streams (default: the built-in minimal markdown). */
  markdown?: (text: string, chat: ChatApi) => string
  /** A finished answer (and restored ones): replaces the bubble's content. */
  assistant?: (text: string, chat: ChatApi) => Out
  /** The user's message bubble content. */
  user?: (text: string, files: string[], chat: ChatApi) => Out
  /** The empty chat. */
  empty?: (data: { title: string; intro: string; starters: string[] }, chat: ChatApi) => Out
  /** The header (logo, title, New chat, Close). */
  header?: (data: { title: string; subtitle: string; newChat: () => void; close: () => void }, chat: ChatApi) => Out
  /** A failed turn: the message and a retry. */
  error?: (data: { message: string; kind: string; text: string; retry: () => void }, chat: ChatApi) => Out
  /** Quick replies under the last answer. */
  suggestions?: (items: string[], chat: ChatApi) => Out
  /** Sources under an answer (from plugins such as formguide). */
  sources?: (items: { title: string; section?: string; quote?: string }[], chat: ChatApi) => Out
  /** The bubble's launcher content (the widget keeps the click and the unread dot). */
  launcher?: (data: { open: boolean; unread: boolean }, chat: ChatApi) => Out
  /** The composer: build your own and call chat.send(text). */
  composer?: (chat: ChatApi) => Out
}

/** An action of your own under an answer: a button with an icon, its label as the tooltip (and `hint` under it). */
export interface MessageAction { id: string; label: string; icon?: string; hint?: string }

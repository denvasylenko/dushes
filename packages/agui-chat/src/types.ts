/** AG-UI wire types the chat uses (a subset of @ag-ui/core, kept local so the package has no dependencies). */

export type Role = 'user' | 'assistant' | 'tool' | 'system'

export interface ToolCall { id: string; type: 'function'; function: { name: string; arguments: string } }

export interface Message {
  id: string
  role: Role
  content?: string
  toolCalls?: ToolCall[]
  toolCallId?: string
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
  /** Files in the composer: the paperclip button uploads them here; they go with the next message. */
  attach?: { accept?: string; upload: (file: File, chat: ChatApi) => Promise<Attachment> }
  /** Load a saved conversation for a thread id. */
  restore?: (threadId: string, chat: ChatApi) => Promise<Restored | null>
}

/** The part of the element plugins and renderers may use. */
export interface ChatApi {
  readonly threadId: string
  readonly options: ChatOptions
  readonly busy: boolean
  /** Files attached in the composer for the message being sent (plugins put them into the run). */
  readonly attachments: Attachment[]
  send(text: string): Promise<void>
  /** Run the agent without a new message, e.g. run({ forwardedProps: { prefill: {...} } }). */
  run(opts?: { forwardedProps?: Record<string, unknown>; notice?: string }): Promise<void>
  notice(text: string): void
  t(key: string, vars?: Record<string, string | number>): string
  host: HTMLElement
}

export interface ChatOptions {
  /** AG-UI run endpoint (POST, SSE). */
  url: string
  threadId?: string
  /** Keep the thread id in localStorage so a reload continues the chat. */
  persistThread: boolean
  mode: 'floating' | 'inline' | 'page'
  /** words: typewriter + fade-in; plain: text as it arrives; off: text when the message ends. */
  typing: 'words' | 'plain' | 'off'
  toolSteps: boolean
  mic: boolean
  quickReplies: boolean
  theme: 'auto' | 'light' | 'dark'
  lang: string
  title: string
  subtitle: string
  intro: string
  placeholder: string
  starters: string[]
  /** How to answer an interrupt: forwardedProps.command.resume (CopilotKit, ag-ui-langgraph) or AG-UI 1.0 resume[]. */
  resumeStyle: 'command' | 'resume'
  /** Send the whole conversation each run (AG-UI default) or only the new messages (server keeps history). */
  history: 'full' | 'last'
  headers: Record<string, string>
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
  /** Show the paperclip when a plugin (or `upload`) can upload files. */
  attach: boolean
  /** File types the paperclip offers, e.g. ".pdf,.jpg"; empty = what the plugin accepts. */
  attachAccept: string
  /** Allow several files at once. */
  attachMultiple: boolean
  /** Largest file in MB; bigger files are refused with a message. */
  attachMaxMb: number
  /** Your own uploader (overrides the plugin's): file -> {id, filename}. */
  upload?: (file: File, chat: ChatApi) => Promise<Attachment>
}

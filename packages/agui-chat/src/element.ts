/** <agui-chat>: an AG-UI chat as a Web Component. Every option: site/src/content/docs/reference/agui-chat.md. */
import { easeHeight, h, md, reducedMotion, store } from './dom'
import { STRINGS } from './i18n'
import { loadZoom } from '#editor-loader'
import { LANGUAGES, PACKS, loadLanguage } from './langs'
import { shrinkImage } from './image'
import { dictate, recognitionBlocked, record, recordingSupported, speechReliable, speechSupported, type Dictation } from './speech'
import { CSS } from './styles'
import { loadTip } from '#tip-loader'
import type { TipRow } from './tip'
import { hasTheme, themeCss, THEME_PACKS, loadTheme } from './themes'
import { watchParts } from './parts'
import { runAgent, runHttp, uid, type AgentLike } from './transport'
import { fadeWords, newState, step, visible, type TypewriterState } from './typewriter'
import type {
  AguiEvent, Attachment, ChatApi, ChatOptions, FrontendTool, IconName, Interrupt, Message, Plugin, Renderer, ReplyTo, RequestKind, RunAgentInput, Slots, ToolCall,
} from './types'

/** A quote: plain text, whitespace collapsed, at most 300 characters (cut with an ellipsis). */
const quoteOf = (s: string): string => {
  const t = s.replace(/\s+/g, ' ').trim()
  return t.length > 300 ? `${t.slice(0, 299).trimEnd()}\u2026` : t
}

/** The selected text without a word cut at either end ("f the amount Af" -> "the amount"); a selection inside one
 * word stays as it is. */
const wholeWords = (range: Range): string => {
  const all = range.toString()
  const letter = /[\p{L}\p{N}]/u
  const a = range.startContainer.textContent ?? '', b = range.endContainer.textContent ?? ''
  let s = all
  if (range.startContainer.nodeType === 3 && letter.test(a[range.startOffset - 1] ?? '') && letter.test(s[0] ?? '')) s = s.replace(/^[\p{L}\p{N}]+/u, '')
  if (range.endContainer.nodeType === 3 && letter.test(b[range.endOffset] ?? '') && letter.test(s[s.length - 1] ?? '')) s = s.replace(/[\p{L}\p{N}]+$/u, '')
  return s.trim() ? s : all
}

/** reply_to as sent or restored: a list (one object from an old server counts as a list of one), empty quotes left out. */
const replyList = (v: ReplyTo | ReplyTo[] | null | undefined): ReplyTo[] =>
  (Array.isArray(v) ? v : v ? [v] : []).filter((r) => r && r.message_id !== undefined && (r.whole || (r.quote ?? '').trim())).slice(0, 10)

export const DEFAULTS: ChatOptions = {
  url: '/agent/run', threadId: undefined, persistThread: true, mode: 'floating', typing: 'words', toolSteps: true, mic: true, quickReplies: true,
  theme: 'default', scheme: '', lang: '', title: '', subtitle: '', intro: '', placeholder: '', footnote: '', starters: [], resumeStyle: 'command',
  history: 'full', headers: {}, credentials: undefined, fetch: undefined, request: undefined, transport: undefined,
  forwardedProps: {}, state: undefined, typingSpeed: 55, fadeMs: 450, toolLabels: {}, i18n: {},
  cards: {}, open: false, micLang: '', micAutoSend: false, voice: 'auto', dictation: '', transcribeUrl: '', attach: true, attachAccept: '', attachMultiple: true,
  attachMaxMb: 20, imageMaxPx: 2000, upload: undefined, icons: {}, render: {},
  bubbleSide: 'right', greeting: '', greetingDelay: 4, motion: 'spring', messageActions: ['copy', 'reply'], onMessageAction: undefined, modal: true, launcher: 'auto', launcherLabel: '', reply: true, composerShadow: 'soft', shortcutHints: true, collapseLines: 8, collapseAnswers: false,
}

/** attribute -> [option, parser] */
const bool = (v: string | null) => v !== null && v !== 'off' && v !== 'false' && v !== 'no'
const ATTRS: Record<string, [keyof ChatOptions, (v: string | null) => unknown]> = {
  url: ['url', String], 'thread-id': ['threadId', String], 'persist-thread': ['persistThread', bool], mode: ['mode', String],
  typing: ['typing', String], 'tool-steps': ['toolSteps', bool], mic: ['mic', bool], 'quick-replies': ['quickReplies', bool],
  theme: ['theme', String], scheme: ['scheme', String], lang: ['lang', String], title: ['title', String], subtitle: ['subtitle', String],
  intro: ['intro', String], placeholder: ['placeholder', String], footnote: ['footnote', String], 'resume-style': ['resumeStyle', String],
  history: ['history', String], open: ['open', bool], attach: ['attach', bool], 'mic-lang': ['micLang', String],
  'mic-auto-send': ['micAutoSend', bool], voice: ['voice', String], dictation: ['dictation', String], 'transcribe-url': ['transcribeUrl', String], 'attach-accept': ['attachAccept', String], 'attach-multiple': ['attachMultiple', bool],
  'attach-max-mb': ['attachMaxMb', Number], 'image-max-px': ['imageMaxPx', Number],
  'bubble-side': ['bubbleSide', String], greeting: ['greeting', String], 'greeting-delay': ['greetingDelay', Number], motion: ['motion', String],
  reply: ['reply', bool], 'composer-shadow': ['composerShadow', String], 'shortcut-hints': ['shortcutHints', bool], 'collapse-lines': ['collapseLines', Number], 'collapse-answers': ['collapseAnswers', bool], modal: ['modal', bool], launcher: ['launcher', String], 'launcher-label': ['launcherLabel', String],
  'message-actions': ['messageActions', (v) => (!v || /^(off|none|false)$/.test(v) ? [] : v.split(',').map((x) => x.trim()).filter(Boolean))],
}

/** Interrupt reasons of RUN_FINISHED.outcome (AG-UI 1.0) -> the `type` renderers are registered for. */
const REASON_TYPE: Record<string, string> = {
  confirm_field_changes: 'set_fields', ask_user: 'ask', request_file: 'upload', confirm_action: 'confirm',
}

/** The line icons of the actions under an answer (24 grid, 1.8 stroke, round caps). */
const ACT: Record<string, string> = {
  copy: 'M9 9h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V10a1 1 0 0 1 1-1zM5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1',
  done: 'M5 12.5l4.5 4.5L19 7',
  retry: 'M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6',
  speak: 'M4 9v6h4l5 4V5L8 9H4zM16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12',
  like: 'M7 11v9H4v-9h3zm0 0 4-7a2 2 0 0 1 3 2l-1 4h5.5a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 17.3 20H7',
  down: 'M12 5v14M6 13l6 6 6-6',
  reply: 'M10 8 5 12.5 10 17M5.5 12.5H14a5 5 0 0 1 5 5V19',
  addChat: 'M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-5 4V6a1 1 0 0 1 1-1zM12 8v6M9 11h6',
}
const actSvg = (d: string): string => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`

const ICON = {
  spark: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" opacity=".7"/></svg>',
  send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/></svg>',
  mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/></svg>',
  // the composer's add button: a plus, as in the Claude app (files and photos now; a menu once a host has commands)
  clip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
}

let sheet: CSSStyleSheet | null = null
/** The base styles (shared) and this element's theme after them; returns a setter for the theme's CSS. */
function styles(root: ShadowRoot): (css: string) => void {
  try {
    sheet ??= new CSSStyleSheet()
    if (!sheet.cssRules.length) sheet.replaceSync(CSS)
    const theme = new CSSStyleSheet()
    root.adoptedStyleSheets = [sheet, theme]   // later sheet, same specificity: the theme wins
    return (css) => theme.replaceSync(css)
  } catch {   // no constructable stylesheets: <style> elements in the same order
    root.appendChild(h('style', null, CSS))
    const theme = root.appendChild(h('style'))
    return (css) => { theme.textContent = css }
  }
}

/** "auto" | "light" | "dark" -> light or dark now. */
const darkNow = (scheme: string): boolean => scheme === 'dark' ||
  (scheme !== 'light' && typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches)

interface AiItem { id: string; text: string; el: HTMLElement; body: HTMLElement; st: TypewriterState; done: boolean; raf: number; typed: () => void }
interface StepsItem { el: HTMLElement; list: HTMLElement; toggle: HTMLButtonElement; text: HTMLElement; steps: Map<string, HTMLElement>; count: number
  t0: number; show?: ReturnType<typeof setTimeout>; last?: { label: string; li: HTMLElement; n: number }; now: string; end?: string }
// one line of steps, hidden (class "quiet") for routine look-ups (plugins' quietSteps) and for the first second
interface PendingCall { id: string; name: string; args: string }

/** After this long with only the dots, a quiet "Still working…" appears. */
const SLOW_MS = 4000

/** A mouse or trackpad: there, moving the focus helps; on a touch screen it would open the keyboard. */
const finePointer = (): boolean => typeof matchMedia !== 'function' || matchMedia('(pointer: fine)').matches

/** The kind of a failed run, for a message in human words (the raw text stays in the tooltip). */
export function errorKind(raw: string): string {
  const m = raw.toLowerCase()
  if (/failed to fetch|networkerror|load failed|network|offline|timed? ?out/.test(m)) return 'errNetwork'
  if (/\b(401|403)\b|unauthori[sz]ed|forbidden|permission/.test(m)) return 'errAccess'
  if (/\b(429|529)\b|rate.?limit|too many|overloaded|busy/.test(m)) return 'errBusy'
  if (/\b5\d\d\b|server error|bad gateway|unavailable/.test(m)) return 'errServer'
  if (/model|anthropic|openai|api.?key|invalid_request|context length|tokens?/.test(m)) return 'errModel'
  return 'error'
}

/** RequestInit headers in any form -> a plain object. */
function headersObject(h: HeadersInit | undefined): Record<string, string> {
  if (!h) return {}
  if (typeof Headers !== 'undefined' && h instanceof Headers) return Object.fromEntries(h.entries())
  return Array.isArray(h) ? Object.fromEntries(h) : { ...(h as Record<string, string>) }
}

export class AguiChatElement extends HTMLElement implements ChatApi {
  static observedAttributes = Object.keys(ATTRS)

  readonly renderers = new Map<string, Renderer>()
  readonly tools = new Map<string, FrontendTool>()
  /** An AG-UI agent instance (e.g. @ag-ui/client HttpAgent) to run instead of the built-in transport. */
  agent: AgentLike | null = null

  private _opts: ChatOptions = { ...DEFAULTS }
  private _plugins: Plugin[] = []
  private _labels: Record<string, Record<string, string> | string> = {}
  private _i18n: Record<string, Record<string, string>> = {}
  private _thread = ''
  private _busy = false
  private _built = false
  private _messages: Message[] = []
  private _abort: AbortController | null = null
  private _ai: AiItem | null = null
  private _steps: StepsItem | null = null
  private _stepsAfter = 1000   // an answer quicker than this shows no steps line at all
  private _runT0 = 0
  private _prevQuick: { s: string[]; a: unknown[] } | null = null   // the suggestions a send took away: Stop brings them back
  private _dots: HTMLElement | null = null
  private _quick: HTMLElement | null = null
  private _suggestions: string[] = []
  private _applies: (unknown[] | null)[] = []
  private _starters: string[] = []
  private _pendingCalls: PendingCall[] = []
  private _calls = new Map<string, PendingCall>()
  private _shown = new Set<string>()     // interrupt ids already on screen
  private _interrupted = false
  private _lastRun: Parameters<AguiChatElement['_run']>[0] | null = null
  private _mic: Dictation | null = null
  private _micGen = 0   // a sent message ends a dictation: late results of older ones are dropped
  private _micBefore: string | null = null   // what was typed before the running dictation (kept when it is dropped)
  private _speechBlocked = false   // the browser's recognition failed as blocked: `auto` records for the server
  private _retryRec: (() => void) | null = null   // a failed transcription can be posted again
  private _recClock = 0
  private _files: Attachment[] = []
  private _sending: Attachment[] = []
  private $: Record<string, HTMLElement> = {}
  private _replies: ReplyTo[] = []   // the quotes the next message replies to, in the order they were collected
  /** Messages written while the assistant answers: they wait at the bottom of the log and go one by one. */
  private _queue: { id: string; text: string; replies: ReplyTo[]; files: Attachment[]; el: HTMLElement }[] = []
  private _paused: '' | 'stop' | 'error' = ''   // the queue waits: after Stop, or under a failed answer until Try again
  private _sendNow: string | null = null   // the queued message Send now is for (its turn starts once the current stops)
  private _picked: ReplyTo | null = null   // what the selection capsule would quote
  private _serverVoice = false   // the server said it transcribes (restore: transcription)
  private _selT: ReturnType<typeof setTimeout> | undefined
  private _onSel = (): void => {
    if (this._winOpen() && (this._popBusy() || this.$.pill.contains(this.root.activeElement))) return   // the window's field took the selection
    clearTimeout(this._selT); this._selT = setTimeout(() => this._showPill(), 150)
  }
  /** A tap anywhere but the reply window closes it. */
  private _onDown = (e: Event): void => {
    const p = this.$.pill, c = this.$.cap, path = e.composedPath()
    if (p && ((!p.hidden && !path.includes(p)) || (c && !c.hidden && !path.includes(c)))) this._closePop(true)
  }
  /** Typing right after a selection goes into the reply window's field (no click first); copying still works. */
  private _onKey = (e: KeyboardEvent): void => {
    const p = this.$.pill, f = this.$.popIn as HTMLTextAreaElement | undefined
    if (!p || p.hidden || !f || e.metaKey || e.ctrlKey || e.altKey || e.key.length !== 1 || e.composedPath().some((x) => x instanceof HTMLElement && x.matches('input, textarea, select, [contenteditable]'))) return
    f.focus({ preventScroll: true })   // the key lands in the field
  }
  private root!: ShadowRoot

  get threadId(): string { return this._thread }
  get attachments(): Attachment[] { return this._sending }
  get busy(): boolean { return this._busy }
  get host(): HTMLElement { return this }
  get options(): ChatOptions { return this._opts }
  /** Merge options; unknown keys are ignored with a warning. Takes effect at once. */
  set options(o: Partial<ChatOptions>) {
    for (const [k, v] of Object.entries(o ?? {})) {
      if (!(k in DEFAULTS)) { console.warn(`agui-chat: unknown option "${k}"`); continue }
      (this._opts as unknown as Record<string, unknown>)[k] = v
    }
    if (o && 'threadId' in o && o.threadId && o.threadId !== this._thread) {
      if (this._built) this._switchThread(o.threadId)
      else this._thread = o.threadId
    }
    else if (o && 'url' in o && this._built && !this._messages.length && !this._opts.threadId) {
      const saved = this._savedThread()   // the thread kept for this endpoint
      if (saved && saved !== this._thread) { this._thread = saved; void this._restore() } else this._setThread(this._thread, true)
    }
    this._apply()
  }
  get plugins(): Plugin[] { return this._plugins }
  set plugins(list: Plugin[]) { this._plugins = []; for (const p of list ?? []) this.use(p) }

  /** Add a plugin: its renderers, frontend tools, step labels and strings. */
  use(p: Plugin): this {
    this._plugins.push(p)
    for (const [k, r] of Object.entries(p.renderers ?? {})) this.renderers.set(k, r)
    for (const tl of p.tools ?? []) this.tools.set(tl.name, tl)
    Object.assign(this._labels, p.toolLabels ?? {})
    for (const [lang, s] of Object.entries(p.i18n ?? {})) this._i18n[lang] = { ...(this._i18n[lang] ?? {}), ...s }
    this._apply()
    if (this._built && p.restore && !this._messages.length) void this._restore()
    return this
  }

  /** Register a frontend tool the agent can call (sent as `tools` with each run). */
  registerTool(tool: FrontendTool): this { this.tools.set(tool.name, tool); return this }

  t(key: string, vars?: Record<string, string | number>): string {
    const lang = this.lang
    const pack = PACKS[lang]
    let s = this._opts.i18n[key] ?? this._i18n[lang]?.[key] ?? pack?.formguide?.[key] ?? pack?.core?.[key] ?? STRINGS[lang]?.[key]
      ?? this._i18n.en?.[key] ?? STRINGS.en[key] ?? key
    for (const [k, v] of Object.entries(vars ?? {})) s = s.replaceAll(`{${k}}`, String(v))
    return s
  }

  get lang(): string {
    const l = this._wantLang()
    return STRINGS[l] || this._i18n[l] || PACKS[l] ? l : 'en'
  }
  private _wantLang(): string {
    return (this._opts.lang || document.documentElement.lang || navigator.language || 'en').slice(0, 2).toLowerCase()
  }
  /** The language's pack is loaded the first time it is needed; the texts switch when it arrives (English until then). */
  private _ensureLang(): void {
    const l = this._wantLang()
    if (PACKS[l] || STRINGS[l] || this._i18n[l] || !LANGUAGES.includes(l)) return
    void loadLanguage(l).then((ok) => {
      if (!ok || !PACKS[l] || !this._built || this._wantLang() !== l) return   // no pack after all: never loop
      this._apply()   // titles, placeholders and the empty chat in the new language
    })
  }

  // ------------------------------------------------------------------ lifecycle
  connectedCallback(): void {
    this._listen(true)
    if (this._built) return
    this._built = true
    this.root = this.attachShadow({ mode: 'open' })
    this._setThemeCss = styles(this.root)
    this.root.addEventListener('click', (e) => this._copyCode(e))
    this._build()
    watchParts(this.root)   // every element gets its part name (parts.ts), also those added later
    this._setThread(this._opts.threadId || this._savedThread() || uid(), false)
    this._apply()
    void this._restore()
    if (this._opts.open) this.open()
  }

  disconnectedCallback(): void { this._listen(false) }

  /** The copy button of a code block in an answer: the code goes to the clipboard, the button says so. */
  private _copyCode(e: Event): void {
    const btn = (e.target as HTMLElement | null)?.closest?.('[data-copy]') as HTMLButtonElement | null
    const code = btn?.parentElement?.querySelector('code')?.textContent
    if (!btn || code == null) return
    const done = (ok: boolean) => {
      btn.textContent = ok ? this.t('copied') : this.t('error')
      setTimeout(() => { btn.textContent = this.t('copy') }, 1500)
    }
    navigator.clipboard?.writeText(code).then(() => done(true), () => done(false)) ?? done(false)
  }

  private _setThemeCss: (css: string) => void = () => {}
  private _themeKey = ''
  private readonly _onScheme = (): void => this._applyTheme()
  private readonly _onThemes = (e: Event): void => {
    const t = this._opts.theme
    if (typeof t !== 'string' || (e as CustomEvent).detail === t || (e as CustomEvent).detail === 'default') { this._themeKey = ''; this._applyTheme() }
  }

  /** The system scheme and newly defined themes, while connected. */
  private _listen(on: boolean): void {
    const mq = typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: dark)') : null
    if (on) { mq?.addEventListener?.('change', this._onScheme); window.addEventListener('agui:themes', this._onThemes); document.addEventListener('selectionchange', this._onSel); document.addEventListener('pointerdown', this._onDown, true); document.addEventListener('keydown', this._onKey, true) }
    else { mq?.removeEventListener?.('change', this._onScheme); window.removeEventListener('agui:themes', this._onThemes); document.removeEventListener('selectionchange', this._onSel); document.removeEventListener('pointerdown', this._onDown, true); document.removeEventListener('keydown', this._onKey, true) }
  }

  /** The scheme ("theme" auto/light/dark still means the scheme) and the theme's CSS. */
  private _applyTheme(): void {
    if (!this._built) return
    const o = this._opts
    const legacy = typeof o.theme === 'string' && ['auto', 'light', 'dark'].includes(o.theme)
    const scheme = o.scheme || (legacy ? o.theme as string : 'auto')
    const theme = legacy || !o.theme ? 'default' : o.theme
    const dark = darkNow(scheme)
    this.classList.toggle('dark', dark)
    this.dataset.scheme = dark ? 'dark' : 'light'
    this.dataset.theme = typeof theme === 'string' ? (hasTheme(theme) ? theme : 'default') : 'custom'
    if (typeof theme === 'string' && !hasTheme(theme) && THEME_PACKS.includes(theme)) {
      void loadTheme(theme)   // defineTheme fires agui:themes, which applies it
      if (this._themeKey !== 'default') { this._themeKey = 'default'; this._setThemeCss(themeCss('default')) }
      return
    }
    const key = typeof theme === 'string' ? theme : JSON.stringify(theme)
    if (key !== this._themeKey) { this._themeKey = key; this._setThemeCss(themeCss(theme)) }
  }

  attributeChangedCallback(name: string, _old: string | null, value: string | null): void {
    const a = ATTRS[name]
    if (a) this.options = { [a[0]]: value === null && name !== 'open' ? DEFAULTS[a[0]] : a[1](value) } as Partial<ChatOptions>
  }

  private get _popup(): boolean { return this._opts.mode === 'floating' || this._opts.mode === 'bubble' }

  open(): void {
    if (!this._popup && !this._hero) return
    const was = this.$.wrap.classList.contains('open')
    this.$.wrap.classList.remove('closing')
    this.$.wrap.classList.add('open')
    this.$.fab.classList.remove('unread')
    this.$.fab.setAttribute('aria-expanded', 'true')
    this._hideGreeting()
    this.$.panel.setAttribute('aria-hidden', 'false')
    if (finePointer()) setTimeout(() => (this.$.input as HTMLTextAreaElement).focus({ preventScroll: true }), 60)   // a phone would open its keyboard
    requestAnimationFrame(() => this.$.log.querySelectorAll<HTMLElement>('.fold-later').forEach((x) => this._fold(x)))   // laid out now
    if (!was) this.dispatchEvent(new CustomEvent('agui:open'))   // the page can hide what the open chat covers
  }

  /** hero mode: the field alone until the first message. */
  private get _hero(): boolean { return this._opts.mode === 'hero' }
  /** hero mode on a phone: the open chat is a full-screen sheet with a close button. */
  private get _heroSheet(): boolean { return this._hero && typeof matchMedia === 'function' && !matchMedia('(min-width: 760px)').matches }

  /** Change the composer's hint (a language switch on the page). */
  setPlaceholder(text: string): void {
    this._opts.placeholder = String(text ?? '')
    if (this._built) { const input = this.$.input as HTMLTextAreaElement; input.placeholder = this._opts.placeholder || this.t('placeholder'); input.setAttribute('aria-label', input.placeholder) }
  }

  close(): void {
    const wasOpen = this.$.wrap.classList.contains('open')
    this.$.wrap.classList.remove('open')
    if (wasOpen && this._opts.mode === 'bubble') {   // a quick shrink back into the launcher
      this.$.wrap.classList.add('closing')
      setTimeout(() => this.$.wrap.classList.remove('closing'), 240)
    }
    this.$.fab.setAttribute('aria-expanded', 'false')
    this.$.panel.setAttribute('aria-hidden', 'true')
    if (this._hero) this.$.panel.removeAttribute('aria-hidden')   // the field stays on the page
    else this.$.fab?.focus()
    if (wasOpen) this.dispatchEvent(new CustomEvent('agui:close'))
  }

  /** The launcher: open when closed, close when open (bubble mode). */
  toggle(): void { if (this.$.wrap.classList.contains('open')) this.close(); else this.open() }

  // ------------------------------------------------------------------ the bubble's greeting
  private _greetTimer = 0
  private _greetKey(): string { return `agui-chat:greeting:${location.pathname}` }
  private _scheduleGreeting(): void {
    clearTimeout(this._greetTimer)
    const o = this._opts
    if (o.mode !== 'bubble' || !o.greeting || store<boolean>(this._greetKey()).get()) { this._hideGreeting(); return }
    this._greetTimer = window.setTimeout(() => {
      if (this.$.wrap.classList.contains('open')) return
      this.$.greetText.textContent = o.greeting
      this.$.greet.hidden = false
      requestAnimationFrame(() => this.$.greet.classList.add('show'))
    }, Math.max(0, o.greetingDelay) * 1000)
  }
  private _hideGreeting(forever = false): void {
    clearTimeout(this._greetTimer)
    this.$.greet?.classList.remove('show')
    if (this.$.greet) this.$.greet.hidden = true
    if (forever) store<boolean>(this._greetKey()).set(true)
  }

  /** Start a new conversation (a new thread id). */
  reset(): void {
    this._switchThread(uid(), false)
  }

  private _switchThread(id: string, restore = true): void {
    this._dropDictation()
    this._setReplies([])
    for (const q of [...this._queue]) this._removeQueued(q.id, false)
    this._paused = ''
    this.stop()
    this._setThread(id, true)
    this._messages = []
    this._shown.clear()
    this._clearQuick()
    if (restore) this._starters = []   // "New chat" keeps the form's starters
    this.$.log.replaceChildren()
    if (restore) void this._restore(); else this._renderEmpty()
  }

  /** Abort the running turn. */
  stop(): void {
    if (!this._abort) return
    for (const p of this._plugins) p.onStop?.(this)
    this._abort.abort()
  }

  async send(text: string): Promise<void> {
    text = String(text ?? '').trim()
    if (!text && this._files.length) text = this.t('useAttached')
    const noted = this._replies.some((r) => r.note)
    if (!text && !noted) return
    if (this._busy) { this._enqueue(text); return }   // the assistant is answering: it waits its turn, at the bottom
    if (this._queue.length && this._paused) { this._enqueue(text); this._paused = ''; this._drain(); return }   // behind the waiting ones, in order
    if (this._hero) this.open()   // the field grows into the chat (a sheet on a phone)
    this._dropDictation()   // a chip or starter answered: the half-dictated text is stale (the composer's own send stopped it already)
    this._clearQuick()
    this.$.log.querySelector('.empty')?.remove()
    this.$.log.querySelector('.resumed')?.remove()   // a new message: the server runs it after the turn it is finishing
    this._closePendingCards()
    this._sending = this._files
    this._files = []
    this._renderFiles()
    const replies = this._replies
    this._setReplies([])
    this._userBubble(text, this._sending.map((f) => f.filename), this._sending.map((f) => this._previews.get(f.id)), replies)
    // the replies are on the quotes: the message still carries a short text so the turn has one
    this._messages.push({ id: uid(), role: 'user', content: text || this.t('quotedReply') })
    const sent = replies.map((r) => ({ message_id: r.message_id, ...(r.whole ? { whole: true } : { quote: r.quote }), ...(r.note ? { note: r.note } : {}) }))
    await this._run(sent.length ? { forwardedProps: { reply_to: sent } } : {})
  }

  /** A request through the chat's connection: headers (object or function), credentials, the request hook
   * and fetch from the options. Runs use it too; plugins use it for their own calls. */
  async request(kind: RequestKind, url: string, init: RequestInit = {}): Promise<Response> {
    const o = this._opts
    const extra = typeof o.headers === 'function' ? await o.headers({ kind, url }) : o.headers
    const headers = { ...headersObject(init.headers), ...(extra ?? {}) }
    let req = { url, init: { ...init, headers, ...(o.credentials ? { credentials: o.credentials } : {}) } as RequestInit }
    if (o.request) req = (await o.request({ kind, ...req })) || req
    return (o.fetch ?? fetch)(req.url, req.init)
  }

  async run(opts: { forwardedProps?: Record<string, unknown>; notice?: string } = {}): Promise<void> {
    if (this._busy) return
    this._dropDictation()
    this._clearQuick()
    this._closePendingCards()
    if (opts.notice) this.notice(opts.notice)
    this._sending = []
    await this._run({ forwardedProps: opts.forwardedProps })
  }

  /** Show a small centred line in the chat. */
  notice(text: string): void { this._append(h('div', { class: 'notice', part: 'notice' }, text)) }

  /** Add an element to the conversation (plugins: sources under an answer, a receipt). */
  append(el: HTMLElement): void { this._append(el) }

  /** A slot from options.render: its element, or null for the default (a throwing slot warns once). */
  renderSlot(name: keyof Slots, ...args: unknown[]): HTMLElement | null {
    const f = this._opts.render?.[name] as ((...a: unknown[]) => unknown) | undefined
    if (!f) return null
    try {
      const out = f(...args, this)
      return out instanceof HTMLElement ? out : null
    } catch (e) {
      if (!this._slotWarned.has(name)) { this._slotWarned.add(name); console.warn(`agui-chat: render.${name} failed, using the default`, e) }
      return null
    }
  }
  private _slotWarned = new Set<string>()
  private _defaultHead: Node[] | null = null
  private _defaultFoot: Node[] | null = null

  /** An icon from options.icons (an SVG string or an element) or the built-in one. */
  private _icon(el: HTMLElement, name: IconName): void {
    const own = this._opts.icons?.[name]
    const label = el.querySelector('.fab-label')
    if (own instanceof HTMLElement) el.replaceChildren(own.cloneNode(true))
    else el.innerHTML = typeof own === 'string' ? own : ICON[name === 'logo' ? 'spark' : name]
    if (label) el.appendChild(label)
  }

  /** The answer's HTML: options.render.markdown or the built-in minimal markdown. */
  private _html(text: string): string {
    const f = this._opts.render?.markdown
    if (f) { try { return f(text, this) } catch (e) { if (!this._slotWarned.has('markdown')) { this._slotWarned.add('markdown'); console.warn('agui-chat: render.markdown failed', e) } } }
    return md(text, { copy: this.t('copy') })
  }

  /** A finished answer: render.assistant may replace its content. */
  private _assistantDone(body: HTMLElement, text: string): void {
    const own = this.renderSlot('assistant', text)
    if (own) body.replaceChildren(own)
    if (this._opts.collapseAnswers && !body.querySelector(':scope > .ans')) {   // a long answer folds too, when asked for
      const box = h('div', { class: 'ans' })
      box.append(...[...body.childNodes].filter((c) => !(c instanceof HTMLElement && c.classList.contains('msg-acts'))))
      body.prepend(box)
      this._fold(box)
    }
    this._actions(body, text)
  }

  // ------------------------------------------------------------------ DOM
  private _build(): void {
    const wrap = h('div', { class: 'wrap' })
    const fabIco = h('span', { class: 'fab-ico', 'aria-hidden': 'true' })
    const fabX = h('span', { class: 'fab-x', 'aria-hidden': 'true' })
    const fabOwn = h('span', { class: 'fab-own' })
    const fab = h('button', { class: 'fab', part: 'fab', type: 'button', 'aria-expanded': 'false', onclick: () => this.toggle() },
      fabIco, fabX, fabOwn, h('span', { class: 'fab-label' }), h('span', { class: 'fab-dot', 'aria-hidden': 'true' }))
    this._icon(fabIco, 'logo'); this._icon(fabX, 'close')
    const greetText = h('span')
    const greet = h('div', { class: 'greet', part: 'greeting', hidden: true, role: 'status' },
      h('button', { class: 'greet-body', type: 'button', onclick: () => this.open() }, greetText),
      h('button', { class: 'greet-x', type: 'button', 'aria-label': this.t('close'), onclick: () => this._hideGreeting(true) }, '\u00d7'))
    const scrim = h('div', { class: 'scrim', onclick: () => this.close() })
    const logo = h('div', { class: 'logo' }); this._icon(logo, 'logo')
    const title = h('div', { class: 'title' }), sub = h('div', { class: 'sub' })
    const btnNew = h('button', { class: 'icon', type: 'button', onclick: () => this.reset() }); this._icon(btnNew, 'plus')
    const btnClose = h('button', { class: 'icon close', type: 'button', onclick: () => this.close() }); this._icon(btnClose, 'close')
    const head = h('div', { class: 'head', part: 'header' }, logo, h('div', null, title, sub), btnNew, btnClose)
    const log = h('div', { class: 'log', part: 'log', role: 'log', 'aria-live': 'polite', 'aria-relevant': 'additions' })
    const input = h('textarea', { rows: 1, part: 'input' }) as HTMLTextAreaElement
    const mic = h('button', { class: 'ib mic', type: 'button' }); this._icon(mic, 'mic')
    // server dictation: the wave and timer take the input's place while recording, then "Transcribing…"
    const recX = h('button', { class: 'ib rec-x', type: 'button' }); this._icon(recX, 'close')
    const bars = h('span', { class: 'bars', 'aria-hidden': 'true' }, ...Array.from({ length: 36 }, () => h('i')))
    const wave = h('div', { class: 'wave', part: 'recording' }, bars, h('span', { class: 'rec-time' }, '0:00'),
      h('span', { class: 'rec-busy', role: 'status' }, h('span', { class: 'dots' }, h('i'), h('i'), h('i')), h('span', { class: 'rec-busy-t' })))
    const clip = h('button', { class: 'ib clip', type: 'button' }); this._icon(clip, 'clip')
    const picker = h('input', { type: 'file', multiple: true, hidden: true }) as HTMLInputElement
    const send = h('button', { class: 'send', type: 'button', part: 'send' }); this._icon(send, 'send')
    const files = h('div', { class: 'files', part: 'attachments' })
    // the quotes the next message replies to: one grey tile each, stacked (several go in one message)
    const replyList = h('div', { class: 'reply-list', part: 'reply', role: 'list', id: 'reply-list', hidden: true })
    const box = h('div', { class: 'box' }, replyList, files, clip, recX, input, wave, mic, send)
    // as in the Claude app, two steps: a small capsule over a selection (Reply), then a reply window (the quote on one
    // line, a field "Reply to …", Add to chat)
    const capReply = h('button', { class: 'cap-b cap-reply', type: 'button' })
    const cap = h('div', { class: 'sel-cap', part: 'selection-menu', role: 'toolbar', hidden: true }, capReply)
    cap.addEventListener('pointerdown', (e) => e.preventDefault())   // the selection stays until Reply reads it
    capReply.addEventListener('click', () => this._openWin())
    const popQ = h('div', { class: 'pop-q', id: 'pop-q' })
    const popIn = h('textarea', { class: 'pop-in', rows: 1 }) as HTMLTextAreaElement
    const popMic = h('button', { class: 'ib pop-mic', type: 'button' }); this._icon(popMic, 'mic')
    const popAdd = h('button', { class: 'ib pop-add', type: 'button' }); popAdd.innerHTML = actSvg(ACT.addChat)
    const popErr = h('div', { class: 'pop-err', role: 'status', 'aria-live': 'polite' })
    const pill = h('div', { class: 'sel-pop', part: 'reply-window', role: 'dialog', 'aria-describedby': 'pop-q', hidden: true }, popQ, h('div', { class: 'pop-row' }, popIn, popMic, popAdd), popErr)
    pill.addEventListener('pointerdown', (e) => { if (e.target !== popIn) e.preventDefault() })   // the button keeps the focus in the field
    popIn.addEventListener('input', () => { popIn.style.height = 'auto'; popIn.style.height = `${Math.min(120, popIn.scrollHeight)}px` })
    popIn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); this._popAdd(); return }   // into the composer, under the others
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); this._closePop(true); return }
    })
    popAdd.addEventListener('click', () => this._popAdd())
    popMic.addEventListener('click', () => this._toggleMic('pop'))
    const hint = h('div', { class: 'hint', 'aria-live': 'polite' })
    // the way back to the latest message when the user has scrolled up; while the assistant works it shows the dots
    const jump = h('button', { class: 'jump', part: 'jump', type: 'button', hidden: true, onclick: () => this._toLatest() },
      h('span', { class: 'jump-ico' }), h('span', { class: 'dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i')))
    ;(jump.firstChild as HTMLElement).innerHTML = actSvg(ACT.down)
    const foot = h('div', { class: 'foot', part: 'composer' }, jump, box, hint, picker)
    const panel = h('section', { class: 'panel', part: 'panel', role: 'dialog' }, head, log, foot)
    wrap.append(scrim, panel, greet, fab)
    this.root.appendChild(wrap)
    this.$ = { jump, wrap, fab, fabIco, fabX, fabOwn, greet, greetText, scrim, panel, head, title, sub, btnNew, btnClose, log, input, mic, send, hint, foot, clip, picker, files, box, logo, recX, wave, bars, replyList, pill, cap, capReply, popQ, popIn, popMic, popAdd, popErr, fabLabel: fab.querySelector('.fab-label') as HTMLElement }
    this._swipe(log)
    recX.addEventListener('click', () => { this._dropDictation(); (input as HTMLTextAreaElement).focus() })
    files.hidden = true
    if (typeof ResizeObserver === 'function') new ResizeObserver(() => { if (this._stick) log.scrollTop = log.scrollHeight }).observe(log)
    log.addEventListener('scroll', () => {
      this._stick = log.scrollHeight - log.scrollTop - log.clientHeight < 120
      jump.hidden = this._stick
      if (!this._winOpen()) this._closePop()   // the capsule goes; an open window moves with its text
    }, { passive: true })
    files.addEventListener('scroll', () => this._fadeFiles(), { passive: true })
    clip.addEventListener('click', () => picker.click())
    picker.addEventListener('change', () => { void this._upload([...(picker.files ?? [])]); picker.value = '' })

    const grow = () => {
      if (box.classList.contains('rec')) return   // hidden behind the wave: measured once it shows again
      input.style.height = 'auto'; input.style.height = `${Math.min(180, input.scrollHeight)}px`
    }
    input.addEventListener('input', () => { grow(); this._syncSend() })
    // a screenshot or a file from the clipboard, or dropped on the composer, is attached like a file from the + button
    const takeFiles = (files: FileList | null | undefined, e: Event) => {
      const list = [...(files ?? [])]
      if (!list.length || clip.hidden) return
      e.preventDefault()
      void this._upload(list)
    }
    input.addEventListener('paste', (e) => takeFiles((e as ClipboardEvent).clipboardData?.files, e))
    box.addEventListener('dragover', (e) => { if (!clip.hidden && (e as DragEvent).dataTransfer?.types.includes('Files')) { e.preventDefault(); box.classList.add('drop') } })
    box.addEventListener('dragleave', () => box.classList.remove('drop'))
    box.addEventListener('drop', (e) => { box.classList.remove('drop'); takeFiles((e as DragEvent).dataTransfer?.files, e) })
    input.addEventListener('keydown', (e) => {
      // Esc takes the last quote back (one at a time)
      if (e.key === 'Escape' && this._replies.length && !box.classList.contains('rec')) { e.preventDefault(); e.stopPropagation(); this._dropReply(this._replies.length - 1); return }
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); this._submit() }
    })
    send.addEventListener('click', () => (this._busy ? this.stop() : this._submit()))
    mic.addEventListener('click', () => this._toggleMic())
    // shortcut tooltips, as in the Claude app: only keys that work here
    const hints = (): boolean => this._opts.shortcutHints !== false
    this._tip(send, panel, () => (this._busy ? [{ label: this.t('stop') }] : [{ label: this.t('send'), keys: ['Enter'] }, { label: this.t('newLine'), keys: ['Shift', 'Enter'] }]), hints)
    this._tip(mic, panel, () => [{ label: this.t('mic') }], hints)
    this._tip(clip, panel, () => [{ label: this.t('attach') }], hints)
    this._tip(popAdd, panel, () => [{ label: this.t('addToChat'), keys: ['Enter'] }], hints)
    this._tip(popMic, panel, () => [{ label: this.t('dictateReply') }], hints)
    // only keys a text field owns anyway (Enter, Shift+Enter, Esc): a web page must not take the browser's (Cmd+D bookmarks)
    send.setAttribute('aria-keyshortcuts', 'Enter')
    panel.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && (!pill.hidden || !cap.hidden)) { e.preventDefault(); this._closePop(true); return }
      if (e.key === 'Escape' && this._busy && !e.defaultPrevented) { e.preventDefault(); this.stop(); return }   // Esc stops the answer first
      if (!this._popup && !(this._heroSheet && this.$.wrap.classList.contains('open'))) return
      if (e.key === 'Escape' && this.$.box.classList.contains('rec')) { e.preventDefault(); this._dropDictation(); return }   // drop the recording first
      if (e.key === 'Escape') { e.preventDefault(); this.close() }
      if (e.key === 'Tab' && (this._opts.modal !== false || innerWidth <= 760)) this._trapFocus(e)
    })
    requestAnimationFrame(() => fab.classList.add('show'))
  }

  private _submit(): void {
    const input = this.$.input as HTMLTextAreaElement
    const text = input.value.trim()
    if (!text && !this._files.length && !this._replies.some((r) => r.note)) {
      this.$.foot.classList.remove('nudge'); void this.$.foot.offsetWidth; this.$.foot.classList.add('nudge')
      return
    }
    this._cancelMic()
    input.value = ''
    input.style.height = 'auto'
    this._syncSend()
    void this.send(text)
  }

  /** Who recognises speech now: the browser, the server (a recording), or nobody (no mic). */
  private _micMode(): 'browser' | 'server' | null {
    const d = this._voice()
    if (d === 'off') return null
    if (d === 'server') return recordingSupported() ? 'server' : null
    if (d === 'auto') {
      if ((this._serverVoice || this._opts.transcribeUrl) && recordingSupported()) return 'server'   // our own server first
      if (speechReliable() && !this._speechBlocked) return 'browser'
      if (recordingSupported()) return 'server'
      return speechSupported() && !this._speechBlocked ? 'browser' : null   // cannot record: the browser's, however it does
    }
    return speechSupported() ? 'browser' : null
  }

  /** `voice`, or the old `dictation` when `voice` is left at its default. */
  private _voice(): 'auto' | 'browser' | 'server' | 'off' {
    const v = this._opts.voice
    if (v && v !== 'auto') return ['browser', 'server', 'off'].includes(v) ? v : 'auto'
    const d = this._opts.dictation
    return d === 'browser' || d === 'server' ? d : 'auto'
  }

  private _transcribeUrl(): string {
    if (this._opts.transcribeUrl) return this._opts.transcribeUrl
    try { return new URL('transcribe', new URL(this._opts.url, location.href)).href } catch { return 'transcribe' }
  }

  /** Where a dictation writes: the composer's field (with its wave for server dictation) or the reply window's. */
  private _micAt: 'composer' | 'pop' = 'composer'
  private _afterMic: (() => void) | null = null   // what runs once a server recording has its text
  private _micField(at = this._micAt): HTMLTextAreaElement { return (at === 'pop' ? this.$.popIn : this.$.input) as HTMLTextAreaElement }
  private _micButton(at = this._micAt): HTMLElement { return at === 'pop' ? this.$.popMic : this.$.mic }

  /** Start or stop dictation in a field. One at a time: the other field's dictation stops first and keeps its text. */
  private _toggleMic(at: 'composer' | 'pop' = 'composer'): void {
    if (this._micButton(at).classList.contains('busy') || (at === 'composer' && this.$.box.classList.contains('busy'))) return   // transcribing: wait for the text
    if (this._mic && this._micAt !== at) {
      if (this._micMode() === 'server') { this._afterMic = () => this._toggleMic(at); this._mic.stop(); return }   // its speech is transcribed first
      this._switchMic()
    }
    if (this._mic) { this._mic.stop(); return }
    this._micAt = at
    this._retryRec = null
    if (this._micMode() === 'server') { this._startRecording(); return }
    const input = this._micField(), button = this._micButton()
    const before = input.value ? input.value.replace(/\s*$/, ' ') : ''
    this._micBefore = input.value
    const gen = ++this._micGen
    this.$.hint.textContent = ''
    const o = this._opts
    this._mic = dictate(o.micLang || o.lang || document.documentElement.lang || navigator.language || 'en-US', (text) => {
      if (gen !== this._micGen) return   // this dictation ended with a sent message
      input.value = before + text
      input.dispatchEvent(new Event('input'))
    }, (on, error) => {
      if (gen !== this._micGen && on) return
      button.classList.toggle('on', on)
      this._icon(button, on ? 'stop' : 'mic')
      button.setAttribute('aria-label', on ? this.t('micStop') : this.t(at === 'pop' ? 'dictateReply' : 'mic'))
      if (!on && gen === this._micGen) {
        this._mic = null
        this._micBefore = null
        if (error === 'denied') (at === 'pop' ? this.$.popErr : this.$.hint).textContent = this.t('micDenied')
        else if (this._voice() === 'auto' && recognitionBlocked(error) && recordingSupported()) {
          this._speechBlocked = true   // the browser's service is blocked or unreachable: record for the server
          this._startRecording()
        } else if (at === 'composer' && o.micAutoSend && !error && input.value.trim()) this._submit()
      }
    })
  }

  /** The other field's mic was pressed: stop this dictation where it is; what it recognised stays in its field. */
  private _switchMic(): void {
    this._micGen++
    const m = this._mic
    this._mic = null
    this._micBefore = null
    m?.abort()
    window.clearInterval(this._recClock)
    this.$.box.classList.remove('rec', 'busy')
    for (const b of [this.$.mic, this.$.popMic]) { b.classList.remove('on', 'busy'); this._icon(b, 'mic'); b.setAttribute('aria-label', this.t(b === this.$.popMic ? 'dictateReply' : 'mic')) }
    this.$.input.dispatchEvent(new Event('input'))   // the composer's field shows again: fit it to its text
  }

  /** Dictation on the server: record, post the recording, put the text into the field. In the composer the wave and
   *  timer take the field's place; in the reply window the mic itself shows it is recording, then transcribing. */
  private _startRecording(): void {
    const at = this._micAt, inBox = at === 'composer'
    const input = this._micField(), mic = this._micButton()
    const before = input.value ? input.value.replace(/\s*$/, ' ') : ''
    this._micBefore = input.value
    const gen = ++this._micGen
    const o = this._opts
    const lang = o.micLang || o.lang || document.documentElement.lang || navigator.language || ''
    const box = this.$.box, hint = this.$.hint
    const bars = [...this.$.bars.children] as HTMLElement[]
    const levels: number[] = bars.map(() => 0)
    const time = this.$.wave.querySelector('.rec-time') as HTMLElement
    ;(this.$.wave.querySelector('.rec-busy-t') as HTMLElement).textContent = this.t('transcribing')
    this.$.recX.setAttribute('aria-label', this.t('micCancel'))
    hint.textContent = ''
    const draw = () => levels.forEach((v, i) => { bars[i].style.height = `${Math.round(3 + v * 22)}px` })
    if (inBox) draw()
    const rec = record({
      level: (v) => { if (gen !== this._micGen || !inBox) return; levels.shift(); levels.push(v); draw() },
      state: (st, error) => {
        if (gen !== this._micGen && st !== 'off') return
        if (inBox) { box.classList.toggle('rec', st !== 'off'); box.classList.toggle('busy', st === 'busy') }
        mic.classList.toggle('on', st === 'rec')
        mic.classList.toggle('busy', st === 'busy')
        this._icon(mic, st === 'rec' ? 'stop' : 'mic')   // a stop square on red while recording, as on iOS
        mic.setAttribute('aria-label', st === 'rec' ? this.t('micStop') : st === 'busy' ? this.t('transcribing') : this.t(inBox ? 'mic' : 'dictateReply'))
        mic.toggleAttribute('aria-busy', st === 'busy')
        window.clearInterval(this._recClock)
        if (st === 'rec' && inBox) {
          const t0 = Date.now()
          time.textContent = '0:00'
          this._recClock = window.setInterval(() => {
            const sec = Math.floor((Date.now() - t0) / 1000)
            time.textContent = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
          }, 500)
        }
        if (st === 'off') input.dispatchEvent(new Event('input'))   // the input is shown again: fit it to the text
        if (st !== 'off' || gen !== this._micGen) return
        this._mic = null
        this._micBefore = null
        const line = inBox ? hint : this.$.popErr   // the window's own line: the composer's may be out of view
        if (error === 'failed') {
          this._afterMic = null
          this._retryRec = () => { this._retryRec = null; this._mic = rec; rec.retry() }
          line.replaceChildren(h('span', null, this.t('micFailed') + ' '),
            h('button', { class: 'btn link', type: 'button', onclick: () => { line.textContent = ''; this._retryRec?.() } }, this.t('retry')))
        } else if (error) {
          this._afterMic = null
          line.textContent = this.t(({ denied: 'micDenied', empty: 'micEmpty', unavailable: 'micUnavailable' } as Record<string, string>)[error])
        } else if (inBox && o.micAutoSend && input.value.trim()) this._submit()
        else if (!this._afterMic) input.focus({ preventScroll: true })
        const next = this._afterMic
        this._afterMic = null
        next?.()
      },
      text: (t) => {
        if (gen !== this._micGen) return
        input.value = before + t
        input.dispatchEvent(new Event('input'))
      },
      transcribe: async (audio) => {
        const fd = new FormData()
        fd.append('file', audio, `dictation.${/mp4/.test(audio.type) ? 'm4a' : /ogg/.test(audio.type) ? 'ogg' : 'webm'}`)
        if (lang) fd.append('language', lang)
        const r = await this.request('transcribe', this._transcribeUrl(), { method: 'POST', body: fd })
        if (!r.ok) throw Object.assign(new Error(`transcribe ${r.status}`), { status: r.status })
        return String(((await r.json()) as { text?: string }).text ?? '')
      },
    })
    this._mic = rec
  }

  /** Another action answered instead (a chip, a card, Skip, New chat): stop dictating and drop what was
   * dictated; text typed before the dictation stays. */
  private _dropDictation(): void {
    if (!this._mic) return
    const input = this._micField()
    const typed = this._micBefore ?? input.value
    this._cancelMic()
    input.value = typed
    input.style.height = 'auto'
    this._syncSend()
  }

  /** The message is being sent: stop dictating at once and ignore whatever it still delivers. */
  private _cancelMic(): void {
    this._micBefore = null
    this._micGen++
    const m = this._mic
    this._mic = null
    m?.abort()
    for (const b of [this.$.mic, this.$.popMic]) { if (!b) continue; b.classList.remove('on', 'busy'); this._icon(b, 'mic') }
  }

  private _syncSend(): void {
    const send = this.$.send as HTMLButtonElement
    this._icon(send, this._busy ? 'stop' : 'send')
    send.setAttribute('aria-label', this._busy ? this.t('stop') : this.t('send'))
    // never disabled: an empty send nudges the composer instead of doing nothing
    send.classList.toggle('idle', !this._busy && !(this.$.input as HTMLTextAreaElement).value.trim() && !this._files.length && !this._replies.some((r) => r.note))
  }

  private _trapFocus(e: KeyboardEvent): void {
    const items = [...this.$.panel.querySelectorAll<HTMLElement>('button, textarea, input, select, a[href]')]
      .filter((x) => !x.hasAttribute('disabled') && x.offsetParent !== null)
    if (!items.length) return
    const first = items[0], last = items[items.length - 1]
    const active = this.root.activeElement
    if (e.shiftKey && active === first) { e.preventDefault(); last.focus() } else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus() }
  }

  private _apply(): void {
    if (!this._built) return
    this._ensureLang()
    const o = this._opts
    const wrap = this.$.wrap
    // the launcher's look: auto (a pill with its label for the panel, a round button for the bubble), round, pill or none
    const look = ['round', 'pill', 'none'].includes(o.launcher) ? o.launcher : o.mode === 'bubble' ? 'round' : 'pill'
    wrap.className = `wrap mode-${o.mode} side-${o.bubbleSide === 'left' ? 'left' : 'right'} motion-${o.motion} launcher-${look} shadow-${['raised', 'none'].includes(o.composerShadow) ? o.composerShadow : 'soft'}${wrap.classList.contains('open') ? ' open' : ''}${wrap.classList.contains('nonmodal') ? ' nonmodal' : ''}`
    this._applyTheme()
    this.classList.toggle('calm', reducedMotion())
    this.style.setProperty('--agui-fade', `${o.fadeMs}ms`)
    this.$.title.textContent = o.title || this.t('title')
    this.$.sub.textContent = o.subtitle || this.t('subtitle')
    this.$.fabLabel.textContent = o.launcherLabel || this.t('open')
    this.$.fab.setAttribute('aria-label', o.launcherLabel || this.t('open'))
    // icons (options.icons) and the host's own header and composer (options.render)
    this._icon(this.$.logo, 'logo'); this._icon(this.$.fabIco, 'logo'); this._icon(this.$.fabX, 'close'); this._icon(this.$.btnNew, 'plus'); this._icon(this.$.btnClose, 'close')
    this._icon(this.$.mic, 'mic'); if (!this._mic || this._micAt !== 'pop') this._icon(this.$.popMic, 'mic'); this._icon(this.$.clip, 'clip'); this._icon(this.$.send, this._busy ? 'stop' : 'send')
    const launcher = this.renderSlot('launcher', { open: wrap.classList.contains('open'), unread: this.$.fab.classList.contains('unread') })
    this.$.fabOwn.replaceChildren(...(launcher ? [launcher] : []))
    this.$.fab.classList.toggle('own', !!launcher)
    this._scheduleGreeting()
    this._defaultHead ??= [...this.$.head.childNodes]
    const head = this.renderSlot('header', { title: o.title || this.t('title'), subtitle: o.subtitle || this.t('subtitle'),
      newChat: () => this.reset(), close: () => this.close() })
    this.$.head.replaceChildren(...(head ? [head] : this._defaultHead))
    this._defaultFoot ??= [...this.$.foot.childNodes]
    const foot = this.renderSlot('composer')
    this.$.foot.replaceChildren(...(foot ? [foot] : this._defaultFoot))
    this._placeQuick()   // the suggestions stay above the composer, the host's own one too
    this.$.btnNew.setAttribute('aria-label', this.t('newChat'))
    this.$.jump.setAttribute('aria-label', this.t('toLatest')); this.$.jump.title = this.t('toLatest')
    this.$.btnClose.setAttribute('aria-label', this.t('close'))
    this.$.replyList.setAttribute('aria-label', this.t('reply'))
    this.$.capReply.textContent = this.t('reply')
    this.$.popMic.setAttribute('aria-label', this.t('dictateReply'))
    this.$.popAdd.setAttribute('aria-label', this.t('addToChat'))
    this.$.pill.setAttribute('aria-label', this.t('reply'))
    if (!o.reply) { this._closePop(); this._setReplies([]) }
    else if (this._replies.length) this._renderReplies()   // the language may have changed
    this.$.panel.setAttribute('aria-label', o.title || this.t('title'))
    // modal: false keeps the page beside the panel usable (a site next to its assistant): no scrim, no focus trap;
    // a phone still gets the sheet over the page
    this.$.wrap.classList.toggle('nonmodal', o.modal === false)
    if (o.mode === 'floating' && o.modal !== false) this.$.panel.setAttribute('aria-modal', 'true'); else this.$.panel.removeAttribute('aria-modal')
    const input = this.$.input as HTMLTextAreaElement
    input.placeholder = o.placeholder || this.t('placeholder')
    this.$.hint.dataset.footnote = o.footnote   // the line under the composer when there is no hint or error
    input.setAttribute('aria-label', input.placeholder)
    this.$.mic.hidden = !o.mic || !this._micMode()
    this.$.mic.setAttribute('aria-label', this.t('mic'))
    const attach = this._plugins.find((p) => p.attach)?.attach
    this.$.clip.hidden = !o.attach || !(o.upload || attach)
    this.$.clip.setAttribute('aria-label', this.t('attach'))
    const accept = o.attachAccept || attach?.accept || ''
    if (accept) this.$.picker.setAttribute('accept', accept); else this.$.picker.removeAttribute('accept')
    ;(this.$.picker as HTMLInputElement).multiple = o.attachMultiple
    this.$.log.querySelectorAll('.steps').forEach((s) => ((s as HTMLElement).hidden = !o.toolSteps || s.classList.contains('quiet')))
    if (this._quick) this._quick.hidden = !o.quickReplies
    const empty = this.$.log.querySelector('.empty')
    if (empty || !this.$.log.children.length) this._renderEmpty()
    this._syncSend()
  }

  private _renderEmpty(): void {
    this.$.log.querySelector('.empty')?.remove()
    if (this.$.log.children.length || this._hero) return   // hero: the page around the field is the empty state
    const starters = this._opts.starters.length ? this._opts.starters : this._starters
    const intro = this._opts.intro || this.t(this._opts.quickReplies && starters.length ? 'intro' : 'introAsk')
    const own = this.renderSlot('empty', { title: this._opts.title || this.t('title'), intro, starters })
    if (own) { this.$.log.appendChild(h('div', { class: 'empty' }, own)); return }
    const el = h('div', { class: 'empty' },
      h('h3', null, this._opts.title || this.t('title')),
      h('p', null, this._opts.intro || this.t(this._opts.quickReplies && starters.length ? 'intro' : 'introAsk')),
      this._opts.quickReplies && starters.length
        ? h('div', { class: 'chips' }, starters.map((s) => h('button', { class: 'chip', part: 'chip', type: 'button', onclick: () => void this.send(s) }, s)))
        : null)
    this.$.log.appendChild(el)
  }

  private _append(el: HTMLElement): HTMLElement {
    this.$.log.querySelector('.empty')?.remove()
    // above the dots, and both above the queue: the queue stays last
    const before = this._dots && this._dots.isConnected ? this._dots : this.$.log.querySelector<HTMLElement>(':scope > .msg.queued')
    this.$.log.insertBefore(el, before)
    if (el.querySelector('.fold-later')) el.querySelectorAll<HTMLElement>('.fold-later').forEach((x) => this._fold(x))
    this._scroll()
    return el
  }

  /** Follow the conversation down, unless the user scrolled up to read (then the jump button brings them back). */
  private _scroll(force = false): void {
    const log = this.$.log
    if (force) this._stick = true
    if (!this._stick) return
    requestAnimationFrame(() => { log.scrollTop = log.scrollHeight })
  }

  /** True while the log is at (or near) its end: new messages scroll it; false once the user scrolled up. */
  private _stick = true

  private _toLatest(): void {
    const log = this.$.log
    this._stick = true
    this.$.jump.hidden = true
    log.scrollTo?.({ top: log.scrollHeight, behavior: globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    if (!log.scrollTo) log.scrollTop = log.scrollHeight
  }

  private _userBubble(text: string, files: string[] = [], previews: (string | undefined)[] = [], reply?: ReplyTo | ReplyTo[] | null): void {
    const quotes = replyList(reply)
    const own = this.renderSlot('user', text, files)
    this._lastUser = text
    // the images and files sit above the bubble, on their own, like a photo sent in Messages
    const el = this._append(h('div', { class: 'msg me', part: 'message user' },
      own ?? [files.length ? h('div', { class: 'att-row', part: 'message-attachments' }, files.map((f, i) => this._tile(f, previews[i]))) : null,
        text || quotes.length ? h('div', { class: 'bubble' }, ...quotes.flatMap((r) => [this._quoteEl(r), r.note ? h('div', { class: 'bq-note' }, r.note) : null]),
          text && text !== this.t('quotedReply') ? (quotes.length ? h('span', { class: 'bubble-text' }, text) : text) : null) : null]))
    const bubble = el.querySelector<HTMLElement>(':scope > .bubble')
    if (bubble) this._fold(bubble)
    void el
    this._scroll(true)   // your own message always brings the view down
  }

  private _lastUser = ''

  // ------------------------------------------------------------------ reply to a part of an answer
  /** The text selected inside one agent message, or null: own messages, cards, tool steps, two messages, nothing. */
  private _selection(): { range: Range; msg: HTMLElement; text: string } | null {
    const root = this.root as ShadowRoot & { getSelection?: () => Selection | null }
    const sel = root.getSelection?.() ?? document.getSelection()
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null
    let range: Range | null = sel.getRangeAt(0)
    if (!this.root.contains(range.startContainer)) {   // Safari: the range is retargeted to the host; ask for the composed one
      const s = sel as Selection & { getComposedRanges?: (...a: unknown[]) => StaticRange[] }
      let c: StaticRange | undefined
      try { c = s.getComposedRanges?.({ shadowRoots: [this.root] })?.[0] } catch { try { c = s.getComposedRanges?.(this.root)?.[0] } catch { c = undefined } }
      if (!c || !this.root.contains(c.startContainer)) return null
      range = document.createRange(); range.setStart(c.startContainer, c.startOffset); range.setEnd(c.endContainer, c.endOffset)
    }
    const at = (n: Node): Element | null => (n.nodeType === 1 ? n as Element : n.parentElement)
    const a = at(range.startContainer), b = at(range.endContainer)
    const msg = a?.closest<HTMLElement>('.msg.ai')
    if (!a || !b || !msg || msg !== b.closest('.msg.ai')) return null
    if ([a, b].some((x) => !x.closest('.body') || x.closest('.card, .steps, .msg-acts, .wait'))) return null
    const text = quoteOf(wholeWords(range))
    return text ? { range, msg, text } : null
  }

  /** Step one: a small capsule over the selection (Reply); a scroll or a tap elsewhere takes it away. */
  private _showPill(): void {
    const cap = this.$.cap
    if (!cap) return
    const s = this._opts.reply ? this._selection() : null
    if (!s) { this._closePop(); return }
    if (!this.$.pill.hidden) this._closePop(true)   // a new selection: the open window keeps what was typed as a tile
    this._picked = { message_id: s.msg.dataset.messageId ?? '', quote: s.text }
    this._anchor = { msg: s.msg, rect: s.range.getBoundingClientRect() }
    this._place(cap)
  }

  private _anchor: { msg: HTMLElement; rect: DOMRect } | null = null

  /** Put the capsule or the window by the selection, in the log (it scrolls with its text, never pinned to an edge):
   *  above it with a mouse, under it on a touch screen (the system's menu is above), right after the quoted message
   *  so Tab reaches it there. */
  private _place(el: HTMLElement): void {
    const a = this._anchor
    if (!a) return
    const log = this.$.log
    if (el.previousElementSibling !== a.msg && el.previousElementSibling?.previousElementSibling !== a.msg) a.msg.after(el)
    el.hidden = false
    const r = a.rect, l = log.getBoundingClientRect()
    const w = el.offsetWidth, ht = el.offsetHeight
    const touch = !!globalThis.matchMedia?.('(pointer: coarse)').matches
    const y = (v: number): number => v - l.top + log.scrollTop   // a point on screen -> a point in the log's content
    let top = y(r.top) - ht - 8
    if (touch || r.top - ht - 8 < l.top) top = y(r.bottom) + (touch ? 28 : 8)   // under it: the system's menu, or no room above
    el.style.left = `${Math.max(8, Math.min(log.clientWidth - w - 8, r.left - l.left + r.width / 2 - w / 2))}px`
    el.style.top = `${Math.max(4, top)}px`
  }

  /** Step two, after Reply: the window with the quote and a field "Reply to …"; the field takes the focus. */
  private _openWin(): void {
    const r = this._picked
    if (!r) return
    this.$.cap.hidden = true
    this.$.popQ.textContent = r.quote ?? ''
    const field = this.$.popIn as HTMLTextAreaElement
    field.placeholder = this.t('replyTo').replace('{name}', this._opts.title || this.t('title'))
    field.setAttribute('aria-label', field.placeholder)
    field.value = ''; field.style.height = 'auto'
    this.$.popMic.hidden = !this._opts.mic || !this._micMode()
    this._place(this.$.pill)
    field.focus({ preventScroll: true })
  }

  /** The user is typing in the reply window (keep it open whatever the page's selection does). */
  private _popBusy(): boolean {
    const p = this.$.pill
    return !!p && !p.hidden && (p.contains(this.root.activeElement) || !!(this.$.popIn as HTMLTextAreaElement).value.trim())
  }

  /** The window is open (it stays through a scroll; the capsule does not). */
  private _winOpen(): boolean { return !!this.$.pill && !this.$.pill.hidden }

  private _closePop(keep = false): void {
    if (!this.$.pill) return
    if (this._mic && this._micAt === 'pop') {   // the window's own dictation ends with it
      if (keep && this._micMode() === 'server') { this._afterMic = () => this._closePop(true); this._mic.stop(); return }   // its words become the tile
      if (keep) this._switchMic(); else this._cancelMic()
    }
    this.$.popErr.textContent = ''
    const typed = (this.$.popIn as HTMLTextAreaElement).value.trim()
    if (keep && typed && this._picked && !this.$.pill.hidden) { this._popAdd(false); return }   // never lose a typed reply
    this.$.pill.hidden = true
    if (this.$.cap) this.$.cap.hidden = true
    this._picked = null
  }

  /** Enter or Add to chat: the quote (with what was typed, as its reply) goes into the composer under the others;
   *  nothing is sent until the user sends the message. */
  private _popAdd(focus = true): void {
    const field = this.$.popIn as HTMLTextAreaElement, r = this._picked
    if (!r) return
    if (this._mic && this._micAt === 'pop') {   // stop dictating here: the words heard so far go with the quote
      if (this._micMode() === 'server') { this._afterMic = () => this._popAdd(focus); this._mic.stop(); return }
      this._switchMic()
    }
    this.$.popErr.textContent = ''
    const note = field.value.trim().slice(0, 1000)
    field.value = ''
    if (!focus) { this._addReply(note ? { ...r, note } : r); this.$.pill.hidden = true; this.$.cap.hidden = true; this._picked = null; return }
    this._replyTo(note ? { ...r, note } : r, false)
  }

  private _clearSelection(): void {
    const root = this.root as ShadowRoot & { getSelection?: () => Selection | null }
    ;(root.getSelection?.() ?? document.getSelection())?.removeAllRanges()
  }

  /** A quote into the composer (at most 10; the same one twice is kept once), the field focused, dictation started. */
  private _replyTo(r: ReplyTo | null, voice: boolean): void {
    if (!r) return
    this._addReply(r)
    this._clearSelection()
    this._closePop()
    if (!(voice && globalThis.matchMedia?.('(pointer: coarse)').matches)) (this.$.input as HTMLTextAreaElement).focus()   // dictating on a phone: no keyboard over the wave
    if (voice && !this._mic) this._toggleMic()
  }

  private _addReply(r: ReplyTo): void {
    const same = (x: ReplyTo): boolean => x.message_id === r.message_id && !!x.whole === !!r.whole && (x.quote ?? '') === (r.quote ?? '')
    const rest = this._replies.filter((x) => !same(x))
    this._setReplies([...rest, r].slice(-10))
  }

  private _setReplies(list: ReplyTo[]): void {
    this._replies = list
    if (!this.$.replyList) return
    this._renderReplies()
    this._syncSend()
  }

  /** Take a quote back, with Undo on the line under the composer for a few seconds (its reply goes with it). */
  private _dropReply(i: number): void {
    const before = this._replies
    if (!before[i]) return
    this._setReplies(before.filter((_, k) => k !== i))
    const hint = this.$.hint
    const undo = h('button', { class: 'btn link', type: 'button', onclick: () => { this._setReplies(before); hint.textContent = '' } }, this.t('undo'))
    hint.replaceChildren(h('span', null, `${this.t('quoteRemoved')} `), undo)
    clearTimeout(this._undoT)
    this._undoT = setTimeout(() => { if (hint.contains(undo)) hint.textContent = '' }, 5000)
  }

  private _undoT: ReturnType<typeof setTimeout> | undefined

  /** One grey tile per quote: the reply icon, the quote on one line, "With reply" when it has one (a tap shows it), x. */
  private _renderReplies(): void {
    const box = this.$.replyList
    box.hidden = !this._replies.length
    box.replaceChildren(...this._replies.map((r, i) => {
      const ico = h('span', { class: 'rc-ico', 'aria-hidden': 'true' }); ico.innerHTML = actSvg(ACT.reply)
      const q = h('span', { class: 'rc-q' }, r.whole ? `${this._opts.title || this.t('title')} \u00b7 ${this._quoteText(r)}` : `\u201c${this._quoteText(r)}\u201d`)
      q.title = q.textContent ?? ''
      const note = r.note ? h('div', { class: 'rc-note-t', hidden: true, id: `rc-note-${i}` }, r.note) : null
      const more = r.note ? h('button', { class: 'rc-note', type: 'button', 'aria-expanded': 'false', 'aria-controls': `rc-note-${i}`,
        onclick: () => { const open = note!.hidden; note!.hidden = !open; more!.setAttribute('aria-expanded', String(open)) } }, this.t('withReply')) : null
      const x = h('button', { class: 'ib rc-x', type: 'button', 'aria-label': `${this.t('cancelReply')}: ${(q.textContent ?? '').slice(0, 40)}`, title: this.t('cancelReply'),
        onclick: () => { this._dropReply(i); (this.$.input as HTMLTextAreaElement).focus() } })
      this._icon(x, 'close')
      return h('div', { class: 'reply-chip', role: 'listitem' }, ico, q, more, x, note)
    }))
    // the field says what it replies to (a screen reader hears it with the field)
    if (this._replies.length) this.$.input.setAttribute('aria-describedby', 'reply-list'); else this.$.input.removeAttribute('aria-describedby')
  }

  /** What a quote shows: the selected text, or for the whole answer its label and the answer's first line. */
  private _quoteText(r: ReplyTo): string {
    if (!r.whole) return r.quote ?? ''
    const el = [...(this.$.log?.querySelectorAll<HTMLElement>('.msg.ai[data-message-id]') ?? [])].find((x) => x.dataset.messageId === r.message_id)
    const body = el?.querySelector<HTMLElement>('.body')
    const first = quoteOf([...(body?.children ?? [])].filter((c) => !c.classList.contains('msg-acts') && !c.classList.contains('fold-btn'))
      .map((c) => (c as HTMLElement).innerText || c.textContent || '').join(' ')).slice(0, 120)
    return first || this.t('wholeAnswer')
  }

  /** Who a whole-answer quote is from (the chat's title, "Assistant"), shown on its first line. */
  private _quoteWho(r: ReplyTo): HTMLElement | null {
    return r.whole ? h('b', { class: 'bq-who' }, this._opts.title || this.t('title')) : null
  }

  /** A long message folds: its start, fading out, and Show more / Show less under it (aria-expanded). */
  private _fold(box: HTMLElement): void {
    const n = Number(this._opts.collapseLines)
    if (!n || n < 1 || box.dataset.fold) return
    if (!box.isConnected || !box.clientHeight) { box.classList.add('fold-later'); return }   // not laid out yet (a closed bubble)
    box.classList.remove('fold-later')
    const cs = getComputedStyle(box)
    const fs = parseFloat(cs.fontSize) || 16, raw = parseFloat(cs.lineHeight)   // px, or a bare number (a multiple of the font size)
    const lh = !raw ? 1.5 * fs : /px$/.test(cs.lineHeight) ? raw : raw * fs
    const quote = box.querySelector<HTMLElement>(':scope > .bubble-q')
    const top = quote ? quote.offsetHeight + (parseFloat(getComputedStyle(quote).marginBottom) || 0) : 0
    const limit = Math.round(top + lh * n + (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0))
    if (box.scrollHeight <= limit + lh * 2) return   // a line or two more is not worth hiding
    box.dataset.fold = '1'
    box.id ||= `fold-${uid()}`
    box.style.setProperty('--fold-h', `${limit}px`)
    box.classList.add('clamped')
    const btn = h('button', { class: 'fold-btn', part: 'fold-toggle', type: 'button', 'aria-expanded': 'false', 'aria-controls': box.id }, this.t('showMore')) as HTMLButtonElement
    const toggle = (): void => {
      const log = this.$.log, top = box.getBoundingClientRect().top
      log.style.overflowAnchor = 'none'
      let open = false
      easeHeight(box, () => { open = box.classList.toggle('clamped') === false })   // it opens and folds, never jumps
      btn.textContent = this.t(open ? 'showLess' : 'showMore')
      btn.setAttribute('aria-expanded', String(open))
      log.scrollTop += box.getBoundingClientRect().top - top   // the text opens downwards from where it was read
      log.style.overflowAnchor = ''
      if (open) return
      const b = btn.getBoundingClientRect(), l = log.getBoundingClientRect()   // folded again: keep the button in view
      if (b.top < l.top || b.bottom > l.bottom) btn.scrollIntoView?.({ block: 'nearest' })
    }
    btn.addEventListener('click', toggle)
    // Tab into a folded answer (a link in it): it opens, so the focus is never on something hidden
    box.addEventListener('focusin', () => { if (box.classList.contains('clamped')) toggle() })
    box.after(btn)
  }

  /** The quote above a user's text: a button to the quoted answer, or plain text when that answer is not in the log. */
  private _quoteEl(r: ReplyTo): HTMLElement {
    const there = [...this.$.log.querySelectorAll<HTMLElement>('.msg.ai[data-message-id]')].some((x) => x.dataset.messageId === r.message_id)
    const t = h('span', { class: 'bq-t' }, this._quoteText(r))
    const label = r.whole ? this.t('wholeAnswer') : null
    return there
      ? h('button', { class: 'bubble-q', part: 'message-quote', type: 'button', title: this.t('toQuoted'), 'aria-label': label ? `${label}: ${t.textContent}` : null,
        onclick: () => this._toQuoted(r.message_id) }, this._quoteWho(r), t)
      : h('div', { class: 'bubble-q', part: 'message-quote', 'aria-label': label ? `${label}: ${t.textContent}` : null }, this._quoteWho(r), t)
  }

  /** A tap on a quote in the user's bubble: the quoted answer, centred and highlighted for a moment. */
  private _toQuoted(id: string): void {
    const el = [...this.$.log.querySelectorAll<HTMLElement>('.msg.ai[data-message-id]')].find((x) => x.dataset.messageId === id)
    if (!el) return
    const calm = !!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    el.scrollIntoView?.({ block: 'center', behavior: calm ? 'auto' : 'smooth' })
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash')
    setTimeout(() => el.classList.remove('flash'), 1300)
  }

  /** On a touch screen, a swipe left on an answer replies to the whole of it (as in Telegram; the iOS back gesture
   *  goes the other way). */
  private _swipe(log: HTMLElement): void {
    let msg: HTMLElement | null = null, x0 = 0, y0 = 0, dx = 0, dir: 'x' | 'y' | null = null
    const ico = h('span', { class: 'swipe-ico', 'aria-hidden': 'true' }); ico.innerHTML = actSvg(ACT.reply)
    log.addEventListener('touchstart', (e) => {
      const t = e.touches[0], el = (e.target as HTMLElement).closest?.<HTMLElement>('.msg.ai')
      const selecting = !((this.root as ShadowRoot & { getSelection?: () => Selection | null }).getSelection?.() ?? document.getSelection())?.isCollapsed
      const edge = t.clientX < 24 || t.clientX > innerWidth - 24   // the system's back gesture lives there
      msg = e.touches.length === 1 && this._opts.reply && el && !selecting && !edge && !(e.target as HTMLElement).closest('.card, pre, table, img, .bk-chart, .steps, .msg-acts') ? el : null
      x0 = t.clientX; y0 = t.clientY; dx = 0; dir = null
    }, { passive: true })
    log.addEventListener('touchmove', (e) => {
      if (!msg) return
      const t = e.touches[0], mx = t.clientX - x0, my = t.clientY - y0
      if (!dir && Math.hypot(mx, my) > 10) dir = Math.abs(mx) > Math.abs(my) * 1.5 && mx < 0 ? 'x' : 'y'
      if (dir !== 'x') return
      e.preventDefault()
      dx = Math.max(0, Math.min(72, -mx * 0.6))   // how far left, as a positive distance
      if (!ico.isConnected) msg.append(ico)
      msg.classList.add('swiping')
      msg.style.transform = `translateX(${-dx}px)`
      ico.style.opacity = String(Math.min(1, dx / 56))
      if (dx >= 56 && !ico.classList.contains('go')) navigator.vibrate?.(8)   // a tick: it will reply
      ico.classList.toggle('go', dx >= 56)
    }, { passive: false })
    const end = (): void => {
      if (!msg) return
      const m = msg
      msg = null
      if (dir !== 'x') return
      m.classList.remove('swiping'); m.style.transform = ''
      ico.remove(); ico.classList.remove('go')
      if (dx >= 56) this._replyTo({ message_id: m.dataset.messageId ?? '', whole: true }, false)
    }
    log.addEventListener('touchend', end)
    log.addEventListener('touchcancel', end)
  }

  /** The actions under an answer: copy, try again, read aloud, a good or bad answer, and the host's own. */
  private _actions(body: HTMLElement, text: string): void {
    const list = this._opts.messageActions ?? []
    if (!list.length || body.querySelector(':scope > .msg-acts')) return
    const id = body.closest('[data-message-id]')?.getAttribute('data-message-id') ?? ''
    const bar = h('div', { class: 'msg-acts', part: 'message-actions', role: 'toolbar' })
    const emit = (action: string, pressed?: boolean): boolean => {
      const detail = { id: action, messageId: id || body.parentElement?.getAttribute('data-message-id') || '', text, pressed }
      const handled = this._opts.onMessageAction?.(action, detail) === true
      this.dispatchEvent(new CustomEvent('agui:message-action', { detail }))
      return handled
    }
    for (const a of list) {
      const own = typeof a === 'object' ? a : null
      const kind = own ? own.id : a as string
      const label = own?.label ?? this.t(({ copy: 'copy', retry: 'retry', speak: 'readAloud', like: 'goodAnswer', dislike: 'badAnswer', reply: 'reply' } as Record<string, string>)[kind] ?? kind)
      const b = h('button', { class: `act act-${kind}`, type: 'button', 'aria-label': label, title: own?.hint ? `${label}\n${own.hint}` : label,
        'aria-pressed': kind === 'like' || kind === 'dislike' || kind === 'speak' ? 'false' : null }) as HTMLButtonElement
      b.innerHTML = actSvg(own?.icon ?? ACT[kind === 'dislike' ? 'like' : kind] ?? ACT.done)
      if (kind === 'speak' && !('speechSynthesis' in globalThis)) continue
      if (kind === 'reply' && !this._opts.reply) continue
      b.addEventListener('click', async () => {
        if (emit(kind, b.getAttribute('aria-pressed') === 'true' ? false : b.hasAttribute('aria-pressed') || undefined)) return
        if (kind === 'copy') {
          try { await navigator.clipboard.writeText(text) } catch { return }
          b.innerHTML = actSvg(ACT.done); b.classList.add('done')
          setTimeout(() => { b.innerHTML = actSvg(ACT.copy); b.classList.remove('done') }, 1500)
        } else if (kind === 'reply') {   // the whole answer (a swipe does the same on a phone)
          this._replyTo({ message_id: id || body.parentElement?.getAttribute('data-message-id') || '', whole: true }, false)
        } else if (kind === 'retry') {
          if (this._lastUser && !this._busy) void this.send(this._lastUser)
        } else if (kind === 'speak') {
          const on = b.getAttribute('aria-pressed') !== 'true'
          speechSynthesis.cancel()
          b.setAttribute('aria-pressed', String(on))
          if (on) {
            const u = new SpeechSynthesisUtterance(body.innerText || text); u.lang = this.lang
            u.onend = () => b.setAttribute('aria-pressed', 'false')
            speechSynthesis.speak(u)
          }
        } else if (kind === 'like' || kind === 'dislike') {
          const on = b.getAttribute('aria-pressed') !== 'true'
          bar.querySelectorAll('.act-like, .act-dislike').forEach((x) => x.setAttribute('aria-pressed', 'false'))
          b.setAttribute('aria-pressed', String(on))
        }
      })
      bar.append(b)
    }
    // "Try again" belongs to the latest answer only
    this.$.log.querySelectorAll('.msg-acts .act-retry').forEach((x) => x.remove())
    this.$.log.querySelectorAll('.msg.ai.last').forEach((x) => x.classList.remove('last'))
    body.append(bar)
    body.closest('.msg')?.classList.add('last')
    queueMicrotask(() => body.closest('.msg')?.classList.add('last'))
  }

  private async _upload(list: File[], at?: number): Promise<void> {
    const upload = this._opts.upload ?? this._plugins.find((p) => p.attach)?.attach?.upload
    if (!upload || !list.length) return
    if (!this._opts.attachMultiple) { list = list.slice(0, 1); this._files = [] }
    this.$.hint.textContent = ''   // the tiles show the upload (a spinner on each): no line that would shift the composer
    list = await Promise.all(list.map((f) => shrinkImage(f, this._opts.imageMaxPx)))   // big photos -> JPEG
    const max = this._opts.attachMaxMb * 1024 * 1024
    const big = list.filter((f) => f.size > max)
    list = list.filter((f) => f.size <= max)
    this.$.hint.textContent = big.length ? this.t('tooBig', { name: big.map((f) => f.name).join(', '), mb: this._opts.attachMaxMb }) : ''
    // the tiles appear at once, with a spinner while each file uploads
    const view = (f: File) => (/^image\//.test(f.type) && typeof URL.createObjectURL === 'function' ? URL.createObjectURL(f) : undefined)
    const batch = list.map((f) => ({ key: uid(), name: f.name, preview: view(f) }))
    this._uploading.push(...batch)   // after the ones already there: a second pick never pushes the first aside
    this._renderFiles()
    const done = (u: (typeof batch)[number]): void => { this._uploading = this._uploading.filter((x) => x !== u) }
    try {
      for (let i = 0; i < list.length; i++) {
        const att = await upload(list[i], this)
        if (batch[i].preview) this._previews.set(att.id, batch[i].preview!)
        this._tileKey.set(att.id, batch[i].key)   // the same tile, now done: it stays where it is
        if (at === undefined) this._files.push(att); else this._files.splice(at + i, 0, att)
        done(batch[i])
        this._renderFiles()
      }
    } catch (e) {
      this.$.hint.textContent = `${this.t('error')} ${e instanceof Error ? e.message : String(e)}`
    }
    batch.forEach(done)
    this._renderFiles()
    this._syncSend()
  }

  /** A shortcut tooltip on a button, its code loaded on the first hover or keyboard focus of any of them (it is
   *  only ever needed after half a second of hover); the event that asked for it then plays again. */
  private _tip(button: HTMLElement, host: HTMLElement, rows: () => TipRow[], on: () => boolean): void {
    this._tips.push({ button, host, rows, on })
    const wake = (e: Event): void => {
      if ((e as PointerEvent).pointerType === 'touch' || !on()) return
      for (const t of this._tips) { t.button.removeEventListener('pointerenter', t.wake!); t.button.removeEventListener('focus', t.wake!) }
      void loadTip().then((attach) => {
        for (const t of this._tips) attach(t.button, t.host, t.rows, t.on)
        if (e.type === 'focus') button.dispatchEvent(new FocusEvent('focus'))
        else if (button.matches(':hover')) button.dispatchEvent(new PointerEvent('pointerenter', { pointerType: 'mouse' }))
      }).catch(() => {})   // no tooltip file next to the script: buttons keep their labels
    }
    this._tips[this._tips.length - 1].wake = wake
    button.addEventListener('pointerenter', wake)
    button.addEventListener('focus', wake)
  }

  private _tips: { button: HTMLElement; host: HTMLElement; rows: () => TipRow[]; on: () => boolean; wake?: (e: Event) => void }[] = []

  private _keyed(key: string, tile: HTMLElement): HTMLElement { tile.dataset.key = key; return tile }

  /** A tile for an attachment: an image's thumbnail, or a document's name and type; × removes it from the message. */
  private _tile(name: string, preview: string | undefined, remove?: (tile: HTMLElement) => void, busy = false, edit?: number): HTMLElement {
    const ext = (name.match(/\.([a-z0-9]{1,5})$/i)?.[1] ?? '').toUpperCase()
    const tile = h('span', { class: `att${preview ? '' : ' doc'}${busy ? ' busy' : ''}`, part: 'attachment', title: name },
      preview ? h('button', { class: 'att-open', type: 'button', 'aria-label': name, onclick: (e: Event) => this._zoom(e.currentTarget as HTMLElement, edit === undefined ? undefined : (blob) => this._replaceFile(edit, blob, name)) }, h('img', { src: preview, alt: '' }))
        : [h('span', { class: 'att-name' }, name), ext ? h('span', { class: 'att-ext' }, ext) : null])
    if (remove) tile.append(h('button', { class: 'att-x', type: 'button', 'aria-label': `${this.t('remove')} ${name}`, onclick: () => remove(tile) }, '\u00d7'))
    return tile
  }

  /** The image, large, over the chat (its code loads the first time, with the markup editor). */
  private _zoom(opener: HTMLElement, edit?: (image: Blob) => void): void {
    void loadZoom().then((open) => open({ wrap: this.$.wrap, t: this.t.bind(this), icon: (el, n) => this._icon(el, n) }, opener, edit)).catch(() => {})
  }

  /** Put a marked-up copy in place of an attachment: uploaded like any file, at the same place in the row. */
  private _replaceFile(i: number, image: Blob, name: string): void {
    const file = new File([image], `${name.replace(/\.[a-z0-9]{1,5}$/i, '')}-markup.png`, { type: 'image/png' })
    this._files.splice(i, 1)
    void this._upload([file], i)
  }

  /** Many attachments: the row scrolls sideways, and its edges fade where there is more. */
  private _fadeFiles(): void {
    const f = this.$.files
    f.classList.toggle('more-left', f.scrollLeft > 2)
    f.classList.toggle('more-right', f.scrollLeft + f.clientWidth < f.scrollWidth - 2)
  }

  private _renderFiles(): void {
    // only a tile that was not there before plays its entrance; the others slide to their new place (no jump)
    const was = new Map([...this.$.files.querySelectorAll<HTMLElement>('.att')].map((t) => [t.dataset.key, t.getBoundingClientRect().left]))
    const wasHidden = this.$.files.hidden
    this.$.files.replaceChildren(
      ...this._files.map((f, i) => this._keyed(this._tileKey.get(f.id) ?? f.id, this._tile(f.filename, this._previews.get(f.id), (tile) => {
        const drop = (): void => {
          const k = this._files.indexOf(f)
          if (k >= 0) this._files.splice(k, 1)
          this._renderFiles(); this._syncSend()
        }
        if (reducedMotion() || !tile.animate) drop()
        else { tile.classList.add('att-out'); setTimeout(drop, 180) }   // it shrinks away, then the others close the gap
        if (finePointer()) (this.$.input as HTMLTextAreaElement).focus({ preventScroll: true })   // the composer keeps its focus: no border flash
      }, false, i))),
      ...this._uploading.map((u) => this._keyed(u.key, this._tile(u.name, u.preview, undefined, true))))
    this.$.files.hidden = !this._files.length && !this._uploading.length
    if (wasHidden && !this.$.files.hidden && !reducedMotion()) { this.$.files.classList.remove('files-in'); void this.$.files.offsetWidth; this.$.files.classList.add('files-in') }
    this.$.files.querySelectorAll<HTMLElement>('.att').forEach((t) => {
      const x0 = was.get(t.dataset.key)
      if (x0 === undefined) { t.classList.add('att-new'); return }
      const dx = x0 - t.getBoundingClientRect().left
      if (dx && !reducedMotion()) t.animate?.([{ transform: `translateX(${dx}px)` }, { transform: 'none' }], { duration: 200, easing: 'cubic-bezier(.28, .11, .32, 1)' })
    })
    requestAnimationFrame(() => this._fadeFiles())
  }

  /** Thumbnails of attached images (object URLs) by attachment id, and the files still uploading. */
  private _previews = new Map<string, string>()
  private _uploading: { key: string; name: string; preview?: string }[] = []
  private _tileKey = new Map<string, string>()   // attachment id -> the key its tile had while uploading

  private _showDots(on: boolean): void {
    if (on && !this._dots) {
      const dots = h('div', { class: 'msg ai wait', 'aria-label': this.t('working') }, h('span', { class: 'dots' }, h('i'), h('i'), h('i')))
      this._dots = dots
      this.$.log.insertBefore(dots, this.$.log.querySelector(':scope > .msg.queued'))   // where the answer comes: above the queue
      setTimeout(() => { if (this._dots === dots) dots.appendChild(h('span', { class: 'slow', role: 'status' }, this.t('slow'))) }, SLOW_MS)
      this._scroll()
    } else if (!on && this._dots) {
      this._dots.remove()
      this._dots = null
    }
  }

  private _clearQuick(): void {
    if (this._suggestions.length) this._prevQuick = { s: this._suggestions, a: this._applies }
    this._quick?.remove(); this._quick = null; this._suggestions = []; this._applies = []
  }

  /** The suggestions row goes right above the composer (ours, or the host's own from the composer slot). */
  private _placeQuick(): void {
    if (!this._quick) return
    const foot = this.$.foot
    foot.insertBefore(this._quick, this.$.box.parentNode === foot ? this.$.box : foot.firstChild)
  }

  private _renderQuick(): void {
    this._quick?.remove()
    this._quick = null
    if (!this._suggestions.length) return
    const applier = this._plugins.find((p) => p.applySuggestion)
    const err = h('div', { class: 'muted err-line', role: 'alert' })
    const chips = this._suggestions.map((s, i) => {
      const changes = applier ? this._applies[i] : null
      if (!changes?.length) return h('button', { class: 'chip', part: 'chip', type: 'button', onclick: () => void this.send(s) }, s)
      const b = h('button', { class: 'chip act', part: 'chip', type: 'button', title: this.t('fills') }, h('i', { 'aria-hidden': 'true' }, '\u2713'), s)
      b.addEventListener('click', async () => {   // fill at once, then tell the agent (one tap, no card)
        if (this._busy) return
        this._quick?.querySelectorAll('button').forEach((x) => x.setAttribute('disabled', ''))
        err.textContent = ''
        try {
          const line = await applier!.applySuggestion!(changes, this)
          const sent = this.send(s)
          if (line) this._append(h('div', { class: 'applied' }, line))
          await sent
        } catch (e) {
          this._quick?.querySelectorAll('button').forEach((x) => x.removeAttribute('disabled'))
          err.textContent = e instanceof Error && e.message ? e.message : this.t('error')
        }
      })
      return b
    })
    const own = this.renderSlot('suggestions', this._suggestions)
    // pinned above the composer, one row that scrolls sideways (as in Telegram): the log does not grow under the answer
    this._quick = h('div', { class: 'quick' }, ...(own ? [own] : [h('div', { class: 'chips' }, chips), err]))
    this._quick.hidden = !this._opts.quickReplies
    this._placeQuick()
    const row = this._quick.querySelector<HTMLElement>(':scope > .chips')
    if (row) {
      const fade = (): void => {
        row.classList.toggle('more-left', row.scrollLeft > 2)
        row.classList.toggle('more-right', row.scrollLeft + row.clientWidth < row.scrollWidth - 2)
      }
      row.addEventListener('scroll', fade, { passive: true })
      row.addEventListener('wheel', (e) => {   // a mouse wheel scrolls the row sideways
        if (e.shiftKey || Math.abs(e.deltaY) <= Math.abs(e.deltaX) || row.scrollWidth <= row.clientWidth) return
        row.scrollLeft += e.deltaY; e.preventDefault()
      }, { passive: false })
      requestAnimationFrame(fade)
    }
    if (!this._quick.hidden && !reducedMotion() && typeof this._quick.animate === 'function') {
      const to = this._quick.offsetHeight
      this._quick.animate([{ height: '0px', overflow: 'hidden' }, { height: `${to}px`, overflow: 'hidden' }], { duration: 200, easing: 'cubic-bezier(.2,.8,.2,1)' })
    }
  }

  // ------------------------------------------------------------------ thread
  private _key(): string { return `agui-chat:thread:${location.pathname}:${this._opts.url}` }
  private _savedThread(): string | null { return this._opts.persistThread ? store<string>(this._key()).get() : null }
  private _setThread(id: string, _persist: boolean): void {
    const changed = id !== this._thread
    this._thread = id
    if (this._opts.persistThread) store<string>(this._key()).set(id)
    if (changed) this.dispatchEvent(new CustomEvent('agui:thread', { detail: id }))
  }

  private async _restore(): Promise<void> {
    const p = this._plugins.find((x) => x.restore)
    if (!p?.restore) { this._renderEmpty(); return }
    let r = null
    const seen = this._messages.length
    try { r = await p.restore(this._thread, this) } catch { r = null }
    // a message sent while the history was loading: the live conversation wins over the late history
    if (this._messages.length !== seen || (this._busy && !seen)) return
    if (!r) { this._renderEmpty(); return }
    this._starters = r.starters ?? []
    if (r.transcription) { this._serverVoice = true; this._apply() }
    if (r.messages?.length) {
      // cards are shown, not sent back as history; a reply's quote is drawn, never sent back in messages
      this._messages = r.messages.filter((m) => m.role !== 'activity').map((m) => { const { reply_to, ...rest } = m; void reply_to; return rest })
      this.$.log.replaceChildren()
      this._stick = true
      for (const m of r.messages) {
        if (m.role === 'user' && (m.content || m.reply_to)) this._userBubble(m.content ?? '', [], [], m.reply_to)
        else if (m.role === 'assistant' && m.content) {
          const body = h('div', { class: 'body' }); body.innerHTML = this._html(m.content); this._assistantDone(body, m.content)
          this._append(h('div', { class: 'msg ai', part: 'message assistant', 'data-message-id': m.id }, body))
        } else if (m.role === 'activity') {   // a card shown during that turn (a route, a booking): drawn again in its place
          const value = m.activity ?? (typeof m.content === 'object' ? m.content as Record<string, unknown> : null)
          if (value) this._plugins.some((p) => p.onEvent?.({ type: 'CUSTOM', name: m.activityType ?? 'card', value } as AguiEvent, this) === true)
        }
      }
    }
    if (r.interrupt) this._showInterrupt(r.interrupt, true)
    this._renderEmpty()
    // hero: a turn still running reopens the chat; on a computer, so does a conversation to come back to
    if (this._hero && (r.follow || r.running || (r.messages?.length && !this._heroSheet))) this.open()
    else if (this._opts.mode === 'bubble' && (r.follow || r.running)) this.open()   // the answer is still coming: show it
    if (r.follow) void this._run({ follow: r.follow() })   // the host streams the running turn again: it goes on word by word
    else if (r.running) this._waitForTurn()
    this._loadQueue()
  }

  /** The page was reloaded mid-answer and the server's turn runs on: "Still answering…", then its result. */
  private _waitForTurn(): void {
    const thread = this._thread
    const line = h('div', { class: 'msg ai wait resumed', 'aria-label': this.t('working') },
      h('span', { class: 'dots' }, h('i'), h('i'), h('i')), h('span', { class: 'slow', role: 'status' }, this.t('slow')))
    this.$.log.appendChild(line)
    const check = async () => {
      if (this._thread !== thread || !line.isConnected) return
      const p = this._plugins.find((x) => x.restore)
      let r = null
      try { r = await p!.restore!(thread, this) } catch { r = null }
      if (this._thread !== thread || !line.isConnected) return
      if (r?.running !== false) { setTimeout(check, 2000); return }
      line.remove()
      void this._restore()   // the answer and the card it left
    }
    setTimeout(check, 2000)
  }

  // ------------------------------------------------------------------ runs
  private _input(extra: { forwardedProps?: Record<string, unknown>; resume?: RunAgentInput['resume'] }): RunAgentInput {
    const msgs = this._opts.history === 'last' ? this._tail() : this._messages
    return {
      threadId: this._thread, runId: uid(), messages: msgs, state: this._opts.state ?? {},
      tools: [...this.tools.values()].map(({ name, description, parameters }) => ({ name, description, parameters: parameters ?? { type: 'object', properties: {} } })),
      context: [], forwardedProps: { ...this._opts.forwardedProps, ...(extra.forwardedProps ?? {}) },
      ...(extra.resume ? { resume: extra.resume } : {}),
    }
  }

  /** The messages since the last assistant text: the new user message or the frontend tool results. */
  private _tail(): Message[] {
    let i = this._messages.length
    while (i > 0 && !(this._messages[i - 1].role === 'assistant' && this._messages[i - 1].content)) i--
    return this._messages.slice(i)
  }

  private async _run(args: { resume?: { card_id: string; value: unknown }; forwardedProps?: Record<string, unknown>; follow?: AsyncIterable<AguiEvent> }): Promise<void> {
    this._runT0 = Date.now()
    if (!args.follow) this._lastRun = args   // Try again re-runs a request, never a followed stream
    const extra: Parameters<AguiChatElement['_input']>[0] = { forwardedProps: args.forwardedProps }
    if (args.resume) {
      if (this._opts.resumeStyle === 'resume') {
        const v = args.resume.value as { accepted?: boolean } | null
        extra.resume = [v && typeof v === 'object' && v.accepted === false && Object.keys(v).length === 1
          ? { interrupt_id: args.resume.card_id, status: 'cancelled' }
          : { interrupt_id: args.resume.card_id, status: 'resolved', payload: args.resume.value }]
      } else {
        extra.forwardedProps = { ...(extra.forwardedProps ?? {}), command: { resume: args.resume.value } }
      }
    }
    const input = this._input(extra)
    if (!args.follow) for (const p of this._plugins) await p.beforeRun?.(input, this)
    this._setBusy(true)
    this._interrupted = false
    this._pendingCalls = []
    this._calls.clear()
    this._steps = null
    this._ai = null
    this._showDots(true)
    this._abort = new AbortController()
    const signal = this._abort.signal
    this.dispatchEvent(new CustomEvent('agui:run-start', { detail: input }))
    let failed: string | null = null
    try {
      const o = this._opts
      const events = args.follow ?? (o.transport ? o.transport(input, { signal, chat: this })
        : this.agent ? runAgent(this.agent, input, signal)
          : runHttp(o.url, input, { signal, fetch: (url, init) => this.request('run', url, init) }))
      for await (const ev of events) {
        this.dispatchEvent(new CustomEvent('agui:event', { detail: ev }))
        if (this._plugins.some((p) => p.onEvent?.(ev, this) === true)) continue
        this._handle(ev)
        if (ev.type === 'RUN_ERROR') failed = String(ev.message ?? this.t('error'))
      }
    } catch (e) {
      if (!signal.aborted) failed = e instanceof Error ? e.message : String(e)
    }
    const aborted = signal.aborted
    this._abort = null
    this._finishText()
    this._showDots(false)
    this._finishSteps(!!failed || aborted)
    this._setBusy(false)
    if (aborted) {
      if (this._sendNow) { this._dequeue(this._sendNow); return }   // Send now stopped this turn for a queued message
      this._paused = 'stop'; this._queueHints()
      const prev = this._prevQuick
      if (prev && !this._suggestions.length) { this._suggestions = prev.s; this._applies = prev.a as never; this._renderQuick() }   // the choices are back
      this.notice(this.t('stopped')); return
    }
    if (failed) {
      this.dispatchEvent(new CustomEvent('agui:error', { detail: failed }))
      this._paused = 'error'; this._queueHints()   // nothing more fails in a row: it waits for Try again
      const again = () => { el.remove(); if (this._lastRun) void this._run(this._lastRun) }
      const retry = h('button', { class: 'btn sec', type: 'button', onclick: again }, this.t('retry'))
      const own = this.renderSlot('error', { message: failed, kind: errorKind(failed), text: this.t(errorKind(failed)), retry: again })
      const el = this._append(h('div', { class: 'error', role: 'alert' }, ...(own ? [own] : [h('span', { title: failed }, this.t(errorKind(failed))), retry])))
      return
    }
    this.dispatchEvent(new CustomEvent('agui:run-end', { detail: { threadId: this._thread } }))
    this._prevQuick = null
    if (this._pendingCalls.length && !this._interrupted) await this._runFrontendTools()
    else if (!this._interrupted) { const thread = this._thread; void this._typing.then(() => { if (this._thread === thread) this._renderQuick() }) }   // quick replies last
    this._paused = ''
    setTimeout(() => this._drain())   // the next queued message, once this turn has settled
  }

  // ------------------------------------------------------------------ the queue
  /** A message written while the assistant answers: shown at once, last in the log, with Send now, Edit and Remove. */
  private _enqueue(text: string, saved?: { id: string; replies: ReplyTo[] }): void {
    const replies = saved?.replies ?? this._replies
    const files = saved ? [] : this._files
    const last = this._queue.at(-1)
    if (!saved && last && last.text === text && !replies.length && !files.length && !last.replies.length) return   // a double tap queues once
    if (!saved) { this._setReplies([]); this._files = []; this._renderFiles() }
    const id = saved?.id ?? uid()
    const quotes = replyList(replies)
    const bubble = h('div', { class: 'bubble' }, ...quotes.flatMap((r) => [this._quoteEl(r), r.note ? h('div', { class: 'bq-note' }, r.note) : null]),
      text && text !== this.t('quotedReply') ? (quotes.length ? h('span', { class: 'bubble-text' }, text) : text) : null)
    const line = h('div', { class: 'q-line', part: 'queued' },
      h('span', { class: 'q-tag' }, this.t('queued')),
      h('button', { class: 'q-act q-now', type: 'button', onclick: () => this._sendQueuedNow(id) }, this.t('sendNow')),
      h('button', { class: 'q-act q-edit', type: 'button', onclick: () => this._editQueued(id) }, this.t('edit')),
      h('button', { class: 'q-act q-x', type: 'button', onclick: () => this._removeQueued(id) }, this.t('remove')))
    const el = h('div', { class: 'msg me queued', part: 'message user queued', 'data-queue-id': id,
      onclick: (e: Event) => { if (!(e.target as HTMLElement).closest('button')) el.classList.toggle('q-open') } },
      files.length ? h('div', { class: 'att-row', part: 'message-attachments' }, files.map((f) => this._tile(f.filename, this._previews.get(f.id)))) : null, bubble, line)
    this.$.log.querySelector('.empty')?.remove()
    this.$.log.appendChild(el)   // last: the answer and its dots stay above it
    this._queue.push({ id, text, replies, files, el })
    this._saveQueue()
    this._scroll(true)
    this._queueHints()
  }

  /** The first queued message goes now: its bubble stays where it is (last), its line goes, the turn starts. */
  private _drain(): void {
    if (this._busy || !this._queue.length) return
    if (this.$.log.querySelector('.card[data-pending]')) return this._queueHints()   // a question waits for its answer first
    this._dequeue(this._queue[0].id)
  }

  private _dequeue(id: string): void {
    this._sendNow = null
    const i = this._queue.findIndex((q) => q.id === id)
    if (i < 0) return
    const [q] = this._queue.splice(i, 1)
    this._paused = ''
    this._saveQueue()
    q.el.classList.remove('queued')
    q.el.removeAttribute('data-queue-id')
    q.el.setAttribute('part', 'message user')
    const line = q.el.querySelector<HTMLElement>('.q-line')
    if (line) this._collapse(line, () => line.remove())
    // above the rest of the queue: the order is the order they go in
    const first = this.$.log.querySelector<HTMLElement>(':scope > .msg.queued')
    if (first && first !== q.el && q.el.compareDocumentPosition(first) & Node.DOCUMENT_POSITION_PRECEDING) this.$.log.insertBefore(q.el, first)
    this._clearQuick()
    this._closePendingCards()   // a waiting question is answered by this message now (Send now)
    this._sending = q.files
    this._lastUser = q.text
    this._messages.push({ id: uid(), role: 'user', content: q.text || this.t('quotedReply') })
    const sent = q.replies.map((r) => ({ message_id: r.message_id, ...(r.whole ? { whole: true } : { quote: r.quote }), ...(r.note ? { note: r.note } : {}) }))
    this._queueHints()
    void this._run(sent.length ? { forwardedProps: { reply_to: sent } } : {})
  }

  /** Send now: stop the current answer (or skip the waiting question) and send this one. */
  private _sendQueuedNow(id: string): void {
    if (this._busy) { this._sendNow = id; this.stop(); return }
    this._dequeue(id)
  }

  /** Edit: the text goes back into the field (with its quotes), and leaves the queue. */
  private _editQueued(id: string): void {
    const q = this._queue.find((x) => x.id === id)
    if (!q) return
    this._removeQueued(id, false)
    const input = this.$.input as HTMLTextAreaElement
    const draft = input.value.trim()   // a half-typed message is never lost: the queued text goes under it
    input.value = draft ? `${draft}\n${q.text}` : q.text; input.dispatchEvent(new Event('input'))
    if (q.replies.length) this._setReplies([...this._replies, ...q.replies])
    if (q.files.length) { this._files = [...this._files, ...q.files]; this._renderFiles() }
    input.focus()
  }

  /** Remove: the message eases out, with Undo for 5 s (a new chat removes quietly). */
  private _removeQueued(id: string, undoable = true): void {
    const i = this._queue.findIndex((q) => q.id === id)
    if (i < 0) return
    const [q] = this._queue.splice(i, 1)
    q.el.classList.remove('queued')
    this._collapse(q.el, () => q.el.remove())
    this._saveQueue()
    this._queueHints()
    if (!undoable) return
    const hint = this.$.hint
    const undo = h('button', { class: 'btn link', type: 'button', onclick: () => {
      hint.textContent = ''
      q.el.classList.remove('q-out'); q.el.style.removeProperty('height'); q.el.style.removeProperty('overflow')
      q.el.classList.add('queued')
      const at = Math.min(i, this._queue.length)
      this.$.log.insertBefore(q.el, this._queue[at]?.el ?? null)
      this._queue.splice(at, 0, q)
      this._saveQueue()
      this._queueHints()
    } }, this.t('undo'))
    hint.replaceChildren(h('span', null, `${this.t('messageRemoved')} `), undo)
    clearTimeout(this._undoT)
    this._undoT = setTimeout(() => { if (hint.contains(undo)) hint.textContent = '' }, 5000)
  }

  /** A height change eases (no layout jump): the element folds to nothing, then `done`. */
  private _collapse(el: HTMLElement, done: () => void): void {
    if (!el.isConnected || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { done(); return }
    el.style.height = `${el.offsetHeight}px`; el.style.overflow = 'hidden'
    void el.offsetHeight
    el.classList.add('q-out'); el.style.height = '0px'
    let over = false
    const end = (): void => { if (over || !el.classList.contains('q-out')) return; over = true; done() }
    el.addEventListener('transitionend', end, { once: true })
    setTimeout(end, 260)
  }

  /** The line under each queued message: "Queued", or after a question "Sends after you answer the question". */
  private _queueHints(): void {
    const waits = !this._busy && !!this.$.log.querySelector('.card[data-pending]')
    const why = this._busy ? 'queued' : this._paused === 'error' ? 'afterRetry' : this._paused === 'stop' ? 'queuePaused' : waits ? 'afterQuestion' : 'queued'
    for (const q of this._queue) {
      const tag = q.el.querySelector('.q-tag')
      if (tag) tag.textContent = this.t(why, { retry: this.t('retry') })
    }
  }

  /** The queue survives a reload (text and quotes; files are not kept). */
  private _queueKey(): string { return `agui-queue:${this._thread}` }
  private _saveQueue(): void {
    try {
      if (this._queue.length) localStorage.setItem(this._queueKey(), JSON.stringify(this._queue.map(({ id, text, replies }) => ({ id, text, replies }))))
      else localStorage.removeItem(this._queueKey())
    } catch { /* private mode: the queue lives as long as the page */ }
  }
  private _loadQueue(): void {
    let saved: { id: string; text: string; replies: ReplyTo[] }[] = []
    try { saved = JSON.parse(localStorage.getItem(this._queueKey()) ?? '[]') } catch { saved = [] }
    if (!Array.isArray(saved) || !saved.length) return
    for (const q of saved) if (q && typeof q.text === 'string') this._enqueue(q.text, { id: String(q.id || uid()), replies: Array.isArray(q.replies) ? q.replies : [] })
    setTimeout(() => this._drain())
  }

  private _setBusy(on: boolean): void {
    this._busy = on
    this.toggleAttribute('busy', on)
    this.$.jump?.classList.toggle('busy', on)   // "•••" in the jump button: it is still answering below
    // while it answers, Enter puts the message in the queue: the field says so
    const input = this.$.input as HTMLTextAreaElement | undefined
    const touch = !!globalThis.matchMedia?.('(pointer: coarse)').matches
    if (input) input.placeholder = on ? this.t(touch ? 'queueHintTouch' : 'queueHint') : (this._opts.placeholder || this.t('placeholder'))
    this._syncSend()
    this._queueHints()
  }

  private _handle(ev: AguiEvent): void {
    switch (ev.type) {
      case 'TEXT_MESSAGE_START':
        this._startText(ev.messageId)
        break
      case 'TEXT_MESSAGE_CONTENT':
        if (!this._ai || this._ai.id !== ev.messageId) this._startText(ev.messageId)
        this._ai!.text += ev.delta ?? ''
        this._renderText()
        break
      case 'TEXT_MESSAGE_END':
        if (this._ai && this._ai.id === ev.messageId) {
          if (this._ai.text.trim()) this._messages.push({ id: this._ai.id, role: 'assistant', content: this._ai.text })
          this._finishText()
          this._markUnread()
        }
        break
      case 'TOOL_CALL_START': {
        const call = { id: ev.toolCallId, name: ev.toolCallName, args: '' }
        this._calls.set(call.id, call)
        const front = this.tools.get(call.name)
        if (front) this._pendingCalls.push(call)
        if (front ? front.label : this._label(call.name)) this._addStep(call.id, call.name, front?.label)
        break
      }
      case 'TOOL_CALL_ARGS': {
        const c = this._calls.get(ev.toolCallId)
        if (c) c.args += ev.delta ?? ''
        break
      }
      case 'TOOL_CALL_END': {
        const c = this._calls.get(ev.toolCallId)
        if (c) this._messages.push({ id: uid(), role: 'assistant', toolCalls: [toolCall(c)] })
        break
      }
      case 'TOOL_CALL_RESULT':
        this._doneStep(ev.toolCallId)
        this._messages.push({ id: ev.messageId ?? uid(), role: 'tool', toolCallId: ev.toolCallId, content: String(ev.content ?? '') })
        break
      case 'CUSTOM':
        this._custom(ev.name, ev.value)
        break
      case 'RUN_FINISHED':
        for (const it of ev.outcome?.type === 'interrupt' ? ev.outcome.interrupts ?? [] : []) {
          this._showInterrupt({ type: REASON_TYPE[it.reason] ?? it.reason, card_id: it.id, ...(it.metadata ?? {}) }, false)
        }
        break
    }
  }

  private _custom(name: string, value: unknown): void {
    if (name === 'on_interrupt') {
      let v = value
      if (typeof v === 'string') { try { v = JSON.parse(v) } catch { v = { type: 'unknown', text: v } } }
      const it = v as Interrupt
      this._showInterrupt({ ...it, card_id: it.card_id ?? it.id ?? uid() }, false)
    } else if (name === 'text_retract') {   // a lead the server took back: the answer came after the tools
      const id = String((value as { messageId?: string } | null)?.messageId ?? '')
      const el = [...this.$.log.querySelectorAll<HTMLElement>('[data-message-id]')].find((x) => x.dataset.messageId === id)
      if (!el || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { this.removeMessage(id); return }
      el.classList.add('gone')   // fades, then goes; the answer takes its place
      setTimeout(() => this.removeMessage(id), 180)
    } else if (name === 'tool_progress') {
      const p = value as { parent_id?: string; name?: string; input?: unknown }
      void p   // a tool's own sub-steps are not shown: the line names the tool
    } else if (name === 'suggestions') {
      const items = (value as { items?: unknown[] })?.items
      this._suggestions = Array.isArray(items) ? items.map(String).slice(0, 5) : []
      const applies = (value as { applies?: unknown[] })?.applies
      this._applies = this._suggestions.map((_, i) => (Array.isArray(applies) && Array.isArray(applies[i]) ? applies[i] as unknown[] : null))
    }
  }

  // ------------------------------------------------------------------ text and the typewriter
  private _startText(id: string): void {
    this._finishText()
    this._showDots(false)
    const body = h('div', { class: 'body' })
    const el = h('div', { class: 'msg ai', part: 'message assistant', 'data-message-id': id }, body)
    let typed = () => {}
    // cards and quick replies wait for this text to finish typing (they appear after it, never under a half sentence)
    const before = this._typing
    this._typing = Promise.all([before, new Promise<void>((r) => { typed = r })]).then(() => {})
    this._ai = { id, text: '', el, body, st: newState(), done: false, raf: 0, typed }
    this._append(el)
  }

  /** Resolves when the assistant's text on screen has finished typing (at once when nothing is typing). */
  private _typing: Promise<void> = Promise.resolve()

  private get _animate(): boolean { return this._opts.typing === 'words' && !reducedMotion() && !this._noFrames }

  /** No animation frames arrive (a hidden pane, an occluded window, some in-app web views): type without them. */
  private _noFrames = false

  /** The next typing frame; if none comes within 300 ms, the text is put in at once and typing stops for this chat. */
  private _frame(ai: AiItem): void {
    if (ai.raf) return
    let fired = false
    ai.raf = requestAnimationFrame((now) => { fired = true; ai.raf = 0; this._tick(ai, now) })
    setTimeout(() => {
      if (fired) return
      cancelAnimationFrame(ai.raf)
      ai.raf = 0
      this._noFrames = true
      ai.body.innerHTML = this._html(ai.text)
      if (ai.done) { this._assistantDone(ai.body, ai.text); ai.typed() }
      this._scroll()
    }, 300)
  }

  private _renderText(): void {
    const ai = this._ai
    if (!ai) return
    if (this._opts.typing === 'off') return
    // a hidden tab gets the text at once (no frames there, and nobody watches the typing)
    if (!this._animate || document.hidden) { ai.body.innerHTML = this._html(ai.text); if (ai.done) { this._assistantDone(ai.body, ai.text); ai.typed() } this._scroll(); return }
    this._frame(ai)
  }

  private _tick(ai: AiItem, now: number): void {
    ai.raf = 0
    step(ai.st, ai.text, now, this._opts.typingSpeed)
    ai.body.innerHTML = this._html(visible(ai.text, ai.st.shown))
    fadeWords(ai.body, ai.st, now, this._opts.fadeMs)
    const log = this.$.log
    if (log.scrollHeight - log.scrollTop - log.clientHeight < 120) log.scrollTop = log.scrollHeight
    const fading = ai.st.marks.length > 0 && now - ai.st.marks[ai.st.marks.length - 1][1] < this._opts.fadeMs
    if (ai.st.shown < ai.text.length || fading) this._frame(ai)
    else if (ai.done) { ai.body.innerHTML = this._html(ai.text); this._assistantDone(ai.body, ai.text); ai.typed() }   // all typed and faded in: the plain text stays
  }

  /** The message ended: the typewriter finishes on its own; other modes show the full text now. */
  private _finishText(): void {
    const ai = this._ai
    if (!ai) return
    ai.done = true
    this._ai = null
    if (!ai.text.trim()) { ai.el.remove(); ai.typed(); return }
    if (!this._animate || document.hidden || this._abort?.signal.aborted) {
      cancelAnimationFrame(ai.raf); ai.body.innerHTML = this._html(ai.text); this._assistantDone(ai.body, ai.text); ai.typed(); return
    }
    this._frame(ai)
  }

  // ------------------------------------------------------------------ steps
  private _label(name: string): string {
    if (name in this._opts.toolLabels) return this._opts.toolLabels[name]   // '' hides the step
    // a key ending in * labels every tool with that prefix ("show_*": the cards from blocks)
    const l = this._labels[name] ?? Object.entries(this._labels).find(([k]) => k.endsWith('*') && name.startsWith(k.slice(0, -1)))?.[1]
    if (typeof l === 'string') return l
    if (l) return l[this.lang] ?? PACKS[this.lang]?.tools?.[name] ?? l.en ?? Object.values(l)[0]
    const sub = name.includes('.') ? name.split('.').pop()! : name
    const s = sub.replace(/[_-]+/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2').trim()
    return s.charAt(0).toUpperCase() + s.slice(1)
  }

  /** One line of fixed height: the current step, changed in place ("Searching the business documents…"); the chevron
   *  opens the list. It shows only after the first second, so a quick answer has none. */
  private _ensureSteps(): StepsItem {
    if (this._steps) return this._steps
    const list = h('ul', { id: `steps-${uid()}` })
    const text = h('span', { class: 'steps-t' }, this.t('working'))
    const toggle = h('button', { type: 'button', 'aria-expanded': 'false', 'aria-controls': list.id }, h('span', { class: 'mark', 'aria-hidden': 'true' }), text) as HTMLButtonElement
    const el = h('div', { class: 'steps collapsed quiet', part: 'steps', role: 'status' }, toggle, list)
    toggle.addEventListener('click', () => {
      easeHeight(el, () => {   // the list opens and folds, never jumps
        const closed = el.classList.toggle('collapsed')
        el.classList.toggle('openlist', !closed)
        toggle.setAttribute('aria-expanded', String(!closed))
        if (this._steps) this._stepsHead(this._steps)
      })
    })
    el.hidden = true
    this._steps = { el, list, toggle, text, steps: new Map(), count: 0, t0: this._runT0 || Date.now(), now: this.t('working') }
    this._append(el)
    return this._steps
  }

  private _addStep(id: string, name: string, label?: string): void {
    const s = this._ensureSteps()
    const text = label ?? this._label(name)
    if (!text) return
    s.count++
    let li: HTMLElement
    if (s.last && s.last.label === text) {   // the same step again: one row, "(2)"
      li = s.last.li
      li.lastElementChild!.textContent = `${text} (${++s.last.n})`
      li.className = 'run'
    } else {
      li = h('li', { class: 'run' }, h('span', { class: 'mark' }), h('span', null, text))
      s.last = { label: text, li, n: 1 }
      s.list.appendChild(li)
    }
    s.steps.set(id, li)
    s.now = `${text}\u2026`
    this._stepsHead(s)
    if (!this._plugins.some((p) => p.quietSteps?.includes(name)) && !s.show) {   // a real step: the line shows after the first second
      s.show = setTimeout(() => {
        if (this._steps !== s || s.el.classList.contains('done')) return
        s.el.classList.remove('quiet')
        s.el.hidden = !this._opts.toolSteps
        if (this._dots && !s.el.hidden) this._dots.hidden = true   // the line takes the dots' place: one row, no jump
        this._scroll()
      }, Math.max(0, this._stepsAfter - (Date.now() - s.t0)))
    }
  }

  private _doneStep(id: string): void {
    const li = this._steps?.steps.get(id)
    if (li) li.classList.replace('run', 'ok')
  }

  /** The end: the line says how long it took ("Done in 4 s ›"), in the same place; a line never shown stays hidden. */
  private _finishSteps(failed: boolean): void {
    const s = this._steps
    if (!s) return
    clearTimeout(s.show)
    s.el.querySelectorAll('li.run').forEach((x) => x.classList.replace('run', failed ? 'fail' : 'ok'))
    s.end = failed ? this.t('steps', { n: s.count }) : this.t('doneIn', { s: Math.max(1, Math.round((Date.now() - s.t0) / 1000)) })
    s.el.classList.add('done')   // a list the user opened stays open (it does not snap shut under them)
    this._stepsHead(s)
    s.el.removeAttribute('role')
  }

  /** The line's text: the time when done, the count while the list is open (its rows name the steps), else the step. */
  private _stepsHead(s: StepsItem): void {
    s.text.textContent = s.end ?? (s.el.classList.contains('openlist') ? this.t('steps', { n: s.count }) : s.now)
  }

  // ------------------------------------------------------------------ frontend tools
  private async _runFrontendTools(): Promise<void> {
    const calls = this._pendingCalls
    this._pendingCalls = []
    for (const c of calls) {
      const tool = this.tools.get(c.name)!
      let args: unknown = {}
      try { args = c.args ? JSON.parse(c.args) : {} } catch { args = {} }
      let out: unknown
      try {
        out = await tool.handler(args, { render: (el) => { this._append(h('div', { class: 'tool-el' }, el)) }, chat: this })
      } catch (e) {
        out = `The frontend tool failed: ${e instanceof Error ? e.message : String(e)}`
      }
      this._messages.push({ id: uid(), role: 'tool', toolCallId: c.id, content: typeof out === 'string' ? out : JSON.stringify(out ?? 'ok') })
    }
    await this._run({})
  }

  // ------------------------------------------------------------------ interrupts
  /** An answer while the bubble is closed: a dot on the launcher and a short bounce. */
  private _markUnread(): void {
    if (this._opts.mode !== 'bubble' || this.$.wrap.classList.contains('open')) return
    const fab = this.$.fab
    fab.classList.remove('bounce'); void fab.offsetWidth; fab.classList.add('unread', 'bounce')
  }

  /** Show any card without the agent; the promise resolves with the user's answer. */
  /** Replace the suggestions above the composer without a run (e.g. after the page did the booking itself); `[]` clears them. */
  setSuggestions(items: string[]): void {
    this._suggestions = (Array.isArray(items) ? items : []).map(String).filter((s) => s.trim()).slice(0, 5)
    this._applies = []
    this._prevQuick = null
    if (this._busy) return   // shown when the running answer ends
    this._renderQuick()
  }

  /** Take back an assistant message already shown (e.g. a host's "cut" when an action follows the text). */
  removeMessage(id: string): boolean {
    const el = [...this.$.log.querySelectorAll<HTMLElement>('[data-message-id]')].find((x) => x.dataset.messageId === id)
    if (this._ai?.id === id) { cancelAnimationFrame(this._ai.raf); this._ai.typed(); this._ai = null }
    this._messages = this._messages.filter((m) => m.id !== id)
    if (!el) return false
    el.remove()
    return true
  }

  /** Redraw a shown card in place with new data (a host saved a step, applied a style, undid a change). */
  updateCard(id: string, patch: Record<string, unknown>): boolean {
    const rec = this._cardViews.get(id)
    const old = [...this.$.log.querySelectorAll<HTMLElement>('[data-card-id]')].find((x) => x.dataset.cardId === id)
    if (!rec || !old) return false
    const payload = { ...rec.payload, ...patch }
    const el = rec.draw(payload)
    el.dataset.cardId = id
    old.replaceWith(el)
    this._cardViews.set(id, { payload, draw: rec.draw })
    return true
  }

  /** A card that can be redrawn by updateCard: its payload and how to draw it (plugins register display cards). */
  registerCard(id: string, payload: Record<string, unknown>, draw: (payload: Record<string, unknown>) => HTMLElement): void {
    this._cardViews.set(id, { payload, draw })
  }

  private _cardViews = new Map<string, { payload: Record<string, unknown>; draw: (payload: Record<string, unknown>) => HTMLElement }>()

  showCard(payload: Partial<Interrupt> & { type: string }): Promise<unknown> {
    return new Promise((ok) => {
      const it = { ...payload, card_id: payload.card_id ?? uid() } as Interrupt
      this._shown.delete(it.card_id)
      this._showInterrupt(it, false, ok)
      this._markUnread()
    })
  }

  private _showInterrupt(it: Interrupt, restored: boolean, local?: (value: unknown) => void): void {
    if (this._shown.has(it.card_id)) return
    this._shown.add(it.card_id)
    if (!local) this._interrupted = true
    // a card from the agent appears after the text above it has finished typing, like a message after its sentence
    if (!restored && !local) { const thread = this._thread; void this._typing.then(() => { if (this._thread === thread) this._renderCard(it, restored, local) }); return }
    this._renderCard(it, restored, local)
  }

  private _renderCard(it: Interrupt, restored: boolean, local?: (value: unknown) => void): void {
    this._showDots(false)
    const renderer = this.renderers.get(it.type) ?? fallback
    let done = false
    const ctx = {
      chat: this as ChatApi, restored, flags: this._opts.cards[it.type] ?? {},
      t: (k: string, v?: Record<string, string | number>) => this.t(k, v),
      resolve: (value: unknown) => {
        if (done) return
        done = true
        this._dropDictation()   // the card was answered (or skipped) instead of the dictated text
        el.classList.add('done')
        el.querySelectorAll<HTMLElement>('button, input, select, textarea').forEach((x) => {
          if (!x.hasAttribute('data-keep')) x.setAttribute('disabled', '')
        })
        if (local) { local(value); return }   // showCard(): the host gets the answer, no run
        void this._run({ resume: { card_id: it.card_id, value } })
      },
    }
    let el: HTMLElement
    try { el = renderer(it, ctx) } catch (e) { console.error('agui-chat: renderer failed', e); el = fallback(it, ctx) }
    el.classList.add('card')
    el.setAttribute('part', `card card-${it.type}`)
    el.dataset.cardId = it.card_id
    el.dataset.pending = ''
    const orig = ctx.resolve
    ctx.resolve = (v: unknown) => { delete el.dataset.pending; orig(v) }
    // updateCard() redraws it in place, still answering the same question
    this.registerCard(it.card_id, it as unknown as Record<string, unknown>, (p) => {
      const next = renderer(p as unknown as Interrupt, ctx)
      next.classList.add('card'); next.setAttribute('part', `card card-${it.type}`)
      if (!done) next.dataset.pending = ''
      el = next
      return next
    })
    this._append(el)
    if (finePointer()) el.querySelector<HTMLElement>('[autofocus], .chip, .btn.pri')?.focus({ preventScroll: true })
  }

  /** A new message closes cards nobody answered (the server closes them too): they shrink and say so. */
  private _closePendingCards(): void {
    this.$.log.querySelectorAll<HTMLElement>('.card[data-pending]').forEach((el) => {
      delete el.dataset.pending
      el.classList.add('done', 'dismissed')
      el.querySelectorAll<HTMLElement>('button, input, select, textarea').forEach((x) => x.setAttribute('disabled', ''))
      const line = h('div', { class: 'ok-line off' }, h('i', null, '\u2715'), h('span', null, this.t('replaced')))
      const acts = el.querySelector('.acts')
      if (acts) acts.replaceWith(line); else el.appendChild(line)
    })
  }
}

function toolCall(c: PendingCall): ToolCall {
  return { id: c.id, type: 'function', function: { name: c.name, arguments: c.args || '{}' } }
}

/** Shown for an interrupt type nobody registered: the payload and Skip. */
const fallback: Renderer = (it, ctx) => {
  const { type, card_id: _id, ...rest } = it
  void _id
  return h('div', null,
    h('div', { class: 'card-t' }, ctx.t('unknownCard', { type })),
    h('pre', { class: 'raw' }, JSON.stringify(rest, null, 2)),
    h('div', { class: 'acts' }, h('button', { class: 'btn sec', type: 'button', onclick: () => ctx.resolve({ accepted: false }) }, ctx.t('skip'))))
}

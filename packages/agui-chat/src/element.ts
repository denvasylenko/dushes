/** <agui-chat>: an AG-UI chat as a Web Component. Every option: site/src/content/docs/reference/agui-chat.md. */
import { h, md, reducedMotion, store } from './dom'
import { STRINGS } from './i18n'
import { loadEditor } from '#editor-loader'
import { LANGUAGES, PACKS, loadLanguage } from './langs'
import { shrinkImage } from './image'
import { dictate, recognitionBlocked, record, recordingSupported, speechSupported, type Dictation } from './speech'
import { CSS } from './styles'
import { hasTheme, themeCss, THEME_PACKS, loadTheme } from './themes'
import { watchParts } from './parts'
import { runAgent, runHttp, uid, type AgentLike } from './transport'
import { fadeWords, newState, step, visible, type TypewriterState } from './typewriter'
import type {
  AguiEvent, Attachment, ChatApi, ChatOptions, FrontendTool, IconName, Interrupt, Message, Plugin, Renderer, RequestKind, RunAgentInput, Slots, ToolCall,
} from './types'

export const DEFAULTS: ChatOptions = {
  url: '/agent/run', threadId: undefined, persistThread: true, mode: 'floating', typing: 'words', toolSteps: true, mic: true, quickReplies: true,
  theme: 'default', scheme: '', lang: '', title: '', subtitle: '', intro: '', placeholder: '', footnote: '', starters: [], resumeStyle: 'command',
  history: 'full', headers: {}, credentials: undefined, fetch: undefined, request: undefined, transport: undefined,
  forwardedProps: {}, state: undefined, typingSpeed: 55, fadeMs: 450, toolLabels: {}, i18n: {},
  cards: {}, open: false, micLang: '', micAutoSend: false, dictation: 'browser', transcribeUrl: '', attach: true, attachAccept: '', attachMultiple: true,
  attachMaxMb: 20, imageMaxPx: 2000, upload: undefined, icons: {}, render: {},
  bubbleSide: 'right', greeting: '', greetingDelay: 4, motion: 'spring', messageActions: ['copy'], onMessageAction: undefined,
}

/** attribute -> [option, parser] */
const bool = (v: string | null) => v !== null && v !== 'off' && v !== 'false' && v !== 'no'
const ATTRS: Record<string, [keyof ChatOptions, (v: string | null) => unknown]> = {
  url: ['url', String], 'thread-id': ['threadId', String], 'persist-thread': ['persistThread', bool], mode: ['mode', String],
  typing: ['typing', String], 'tool-steps': ['toolSteps', bool], mic: ['mic', bool], 'quick-replies': ['quickReplies', bool],
  theme: ['theme', String], scheme: ['scheme', String], lang: ['lang', String], title: ['title', String], subtitle: ['subtitle', String],
  intro: ['intro', String], placeholder: ['placeholder', String], footnote: ['footnote', String], 'resume-style': ['resumeStyle', String],
  history: ['history', String], open: ['open', bool], attach: ['attach', bool], 'mic-lang': ['micLang', String],
  'mic-auto-send': ['micAutoSend', bool], dictation: ['dictation', String], 'transcribe-url': ['transcribeUrl', String], 'attach-accept': ['attachAccept', String], 'attach-multiple': ['attachMultiple', bool],
  'attach-max-mb': ['attachMaxMb', Number], 'image-max-px': ['imageMaxPx', Number],
  'bubble-side': ['bubbleSide', String], greeting: ['greeting', String], 'greeting-delay': ['greetingDelay', Number], motion: ['motion', String],
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
}
const actSvg = (d: string): string => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`

const ICON = {
  spark: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" opacity=".7"/></svg>',
  send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/></svg>',
  mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/></svg>',
  clip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 11.5l-8.6 8.6a5.5 5.5 0 01-7.8-7.8l8.6-8.6a3.7 3.7 0 015.2 5.2l-8.6 8.6a1.8 1.8 0 01-2.6-2.6l7.9-7.9"/></svg>',
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
interface StepsItem { el: HTMLElement; list: HTMLElement; toggle: HTMLButtonElement; steps: Map<string, HTMLElement>; count: number }
// a step list with only routine look-ups (plugins' quietSteps) stays hidden: class "quiet"
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
      if (!ok || !this._built || this._wantLang() !== l) return
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
    if (on) { mq?.addEventListener?.('change', this._onScheme); window.addEventListener('agui:themes', this._onThemes) }
    else { mq?.removeEventListener?.('change', this._onScheme); window.removeEventListener('agui:themes', this._onThemes) }
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
    if (!text || this._busy) return
    if (this._hero) this.open()   // the field grows into the chat (a sheet on a phone)
    this._dropDictation()   // a chip or starter answered: the half-dictated text is stale (the composer's own send stopped it already)
    this._clearQuick()
    this.$.log.querySelector('.empty')?.remove()
    this.$.log.querySelector('.resumed')?.remove()   // a new message: the server runs it after the turn it is finishing
    this._closePendingCards()
    this._sending = this._files
    this._files = []
    this._renderFiles()
    this._userBubble(text, this._sending.map((f) => f.filename), this._sending.map((f) => this._previews.get(f.id)))
    this._messages.push({ id: uid(), role: 'user', content: text })
    await this._run({})
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
    const box = h('div', { class: 'box' }, files, clip, recX, input, wave, mic, send)
    const hint = h('div', { class: 'hint', 'aria-live': 'polite' })
    // the way back to the latest message when the user has scrolled up; while the assistant works it shows the dots
    const jump = h('button', { class: 'jump', part: 'jump', type: 'button', hidden: true, onclick: () => this._toLatest() },
      h('span', { class: 'jump-ico' }), h('span', { class: 'dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i')))
    ;(jump.firstChild as HTMLElement).innerHTML = actSvg(ACT.down)
    const foot = h('div', { class: 'foot', part: 'composer' }, jump, box, hint, picker)
    const panel = h('section', { class: 'panel', part: 'panel', role: 'dialog' }, head, log, foot)
    wrap.append(scrim, panel, greet, fab)
    this.root.appendChild(wrap)
    this.$ = { jump, wrap, fab, fabIco, fabX, fabOwn, greet, greetText, scrim, panel, head, title, sub, btnNew, btnClose, log, input, mic, send, hint, foot, clip, picker, files, box, logo, recX, wave, bars, fabLabel: fab.lastElementChild as HTMLElement }
    recX.addEventListener('click', () => { this._dropDictation(); (input as HTMLTextAreaElement).focus() })
    files.hidden = true
    log.addEventListener('scroll', () => {
      this._stick = log.scrollHeight - log.scrollTop - log.clientHeight < 120
      jump.hidden = this._stick
    }, { passive: true })
    files.addEventListener('scroll', () => this._fadeFiles(), { passive: true })
    clip.addEventListener('click', () => picker.click())
    picker.addEventListener('change', () => { void this._upload([...(picker.files ?? [])]); picker.value = '' })

    const grow = () => {
      if (box.classList.contains('rec')) return   // hidden behind the wave: measured once it shows again
      input.style.height = 'auto'; input.style.height = `${Math.min(180, input.scrollHeight)}px`
    }
    input.addEventListener('input', () => { grow(); this._syncSend() })
    // a screenshot or a file from the clipboard, or dropped on the composer, is attached like the paperclip's
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
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); this._submit() }
    })
    send.addEventListener('click', () => (this._busy ? this.stop() : this._submit()))
    mic.addEventListener('click', () => this._toggleMic())
    panel.addEventListener('keydown', (e) => {
      if (!this._popup && !(this._heroSheet && this.$.wrap.classList.contains('open'))) return
      if (e.key === 'Escape' && this.$.box.classList.contains('rec')) { e.preventDefault(); this._dropDictation(); return }   // drop the recording first
      if (e.key === 'Escape') { e.preventDefault(); this.close() }
      if (e.key === 'Tab') this._trapFocus(e)
    })
    requestAnimationFrame(() => fab.classList.add('show'))
  }

  private _submit(): void {
    const input = this.$.input as HTMLTextAreaElement
    const text = input.value.trim()
    if (!text && !this._files.length) {
      this.$.foot.classList.remove('nudge'); void this.$.foot.offsetWidth; this.$.foot.classList.add('nudge')
      return
    }
    if (this._busy) return
    this._cancelMic()
    input.value = ''
    input.style.height = 'auto'
    this._syncSend()
    void this.send(text)
  }

  /** Who recognises speech now: the browser, the server (a recording), or nobody (no mic). */
  private _micMode(): 'browser' | 'server' | null {
    const d = this._opts.dictation
    if (d === 'server') return recordingSupported() ? 'server' : null
    if (d === 'auto') return speechSupported() && !this._speechBlocked ? 'browser' : recordingSupported() ? 'server' : null
    return speechSupported() ? 'browser' : null
  }

  private _transcribeUrl(): string {
    if (this._opts.transcribeUrl) return this._opts.transcribeUrl
    try { return new URL('transcribe', new URL(this._opts.url, location.href)).href } catch { return 'transcribe' }
  }

  private _toggleMic(): void {
    if (this.$.box.classList.contains('busy')) return   // transcribing: wait for the text
    if (this._mic) { this._mic.stop(); return }
    this._retryRec = null
    if (this._micMode() === 'server') { this._startRecording(); return }
    const input = this.$.input as HTMLTextAreaElement
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
      this.$.mic.classList.toggle('on', on)
      this._icon(this.$.mic, on ? 'stop' : 'mic')
      this.$.mic.setAttribute('aria-label', on ? this.t('micStop') : this.t('mic'))
      if (!on && gen === this._micGen) {
        this._mic = null
        this._micBefore = null
        if (error === 'denied') this.$.hint.textContent = this.t('micDenied')
        else if (o.dictation === 'auto' && recognitionBlocked(error) && recordingSupported()) {
          this._speechBlocked = true   // the browser's service is blocked or unreachable: record for the server
          this._startRecording()
        } else if (o.micAutoSend && !error && input.value.trim()) this._submit()
      }
    })
  }

  /** Dictation on the server: record, show the wave, post the recording, put the text into the input. */
  private _startRecording(): void {
    const input = this.$.input as HTMLTextAreaElement
    const before = input.value ? input.value.replace(/\s*$/, ' ') : ''
    this._micBefore = input.value
    const gen = ++this._micGen
    const o = this._opts
    const lang = o.micLang || o.lang || document.documentElement.lang || navigator.language || ''
    const box = this.$.box, mic = this.$.mic, hint = this.$.hint
    const bars = [...this.$.bars.children] as HTMLElement[]
    const levels: number[] = bars.map(() => 0)
    const time = this.$.wave.querySelector('.rec-time') as HTMLElement
    ;(this.$.wave.querySelector('.rec-busy-t') as HTMLElement).textContent = this.t('transcribing')
    this.$.recX.setAttribute('aria-label', this.t('micCancel'))
    hint.textContent = ''
    const draw = () => levels.forEach((v, i) => { bars[i].style.height = `${Math.round(3 + v * 22)}px` })
    draw()
    const rec = record({
      level: (v) => { if (gen !== this._micGen) return; levels.shift(); levels.push(v); draw() },
      state: (s, error) => {
        box.classList.toggle('rec', s !== 'off')
        box.classList.toggle('busy', s === 'busy')
        mic.classList.toggle('on', s === 'rec')
        this._icon(mic, s === 'rec' ? 'stop' : 'mic')   // a stop square on red while recording, as on iOS
        mic.setAttribute('aria-label', s === 'rec' ? this.t('micStop') : this.t('mic'))
        window.clearInterval(this._recClock)
        if (s === 'rec') {
          const t0 = Date.now()
          time.textContent = '0:00'
          this._recClock = window.setInterval(() => {
            const sec = Math.floor((Date.now() - t0) / 1000)
            time.textContent = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
          }, 500)
        }
        if (s === 'off') input.dispatchEvent(new Event('input'))   // the input is shown again: fit it to the text
        if (s !== 'off' || gen !== this._micGen) return
        this._mic = null
        this._micBefore = null
        if (error === 'failed') {
          this._retryRec = () => { this._retryRec = null; this._mic = rec; rec.retry() }
          hint.replaceChildren(h('span', null, this.t('micFailed') + ' '),
            h('button', { class: 'btn link', type: 'button', onclick: () => { hint.textContent = ''; this._retryRec?.() } }, this.t('retry')))
        } else if (error) {
          hint.textContent = this.t(({ denied: 'micDenied', empty: 'micEmpty', unavailable: 'micUnavailable' } as Record<string, string>)[error])
        } else if (o.micAutoSend && input.value.trim()) this._submit()
        else input.focus({ preventScroll: true })
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
    const input = this.$.input as HTMLTextAreaElement
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
    this.$.mic.classList.remove('on')
    this._icon(this.$.mic, 'mic')
  }

  private _syncSend(): void {
    const send = this.$.send as HTMLButtonElement
    this._icon(send, this._busy ? 'stop' : 'send')
    send.setAttribute('aria-label', this._busy ? this.t('stop') : this.t('send'))
    // never disabled: an empty send nudges the composer instead of doing nothing
    send.classList.toggle('idle', !this._busy && !(this.$.input as HTMLTextAreaElement).value.trim() && !this._files.length)
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
    wrap.className = `wrap mode-${o.mode} side-${o.bubbleSide === 'left' ? 'left' : 'right'} motion-${o.motion}${wrap.classList.contains('open') ? ' open' : ''}`
    this._applyTheme()
    this.classList.toggle('calm', reducedMotion())
    this.style.setProperty('--agui-fade', `${o.fadeMs}ms`)
    this.$.title.textContent = o.title || this.t('title')
    this.$.sub.textContent = o.subtitle || this.t('subtitle')
    this.$.fabLabel.textContent = this.t('open')
    // icons (options.icons) and the host's own header and composer (options.render)
    this._icon(this.$.logo, 'logo'); this._icon(this.$.fabIco, 'logo'); this._icon(this.$.fabX, 'close'); this._icon(this.$.btnNew, 'plus'); this._icon(this.$.btnClose, 'close')
    this._icon(this.$.mic, 'mic'); this._icon(this.$.clip, 'clip'); this._icon(this.$.send, this._busy ? 'stop' : 'send')
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
    this.$.btnNew.setAttribute('aria-label', this.t('newChat'))
    this.$.jump.setAttribute('aria-label', this.t('toLatest')); this.$.jump.title = this.t('toLatest')
    this.$.btnClose.setAttribute('aria-label', this.t('close'))
    this.$.panel.setAttribute('aria-label', o.title || this.t('title'))
    if (o.mode === 'floating') this.$.panel.setAttribute('aria-modal', 'true'); else this.$.panel.removeAttribute('aria-modal')
    if (o.mode === 'bubble') this.$.fab.setAttribute('aria-label', this.t('open'))
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
    const before = this._dots && this._dots.isConnected ? this._dots : null
    this.$.log.insertBefore(el, before)
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

  private _userBubble(text: string, files: string[] = [], previews: (string | undefined)[] = []): void {
    const own = this.renderSlot('user', text, files)
    this._lastUser = text
    // the images and files sit above the bubble, on their own, like a photo sent in Messages
    const el = this._append(h('div', { class: 'msg me', part: 'message user' },
      own ?? [files.length ? h('div', { class: 'att-row', part: 'message-attachments' }, files.map((f, i) => this._tile(f, previews[i]))) : null,
        text ? h('div', { class: 'bubble' }, text) : null]))
    void el
    this._scroll(true)   // your own message always brings the view down
  }

  private _lastUser = ''

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
      const label = own?.label ?? this.t(({ copy: 'copy', retry: 'retry', speak: 'readAloud', like: 'goodAnswer', dislike: 'badAnswer' } as Record<string, string>)[kind] ?? kind)
      const b = h('button', { class: `act act-${kind}`, type: 'button', 'aria-label': label, title: own?.hint ? `${label}\n${own.hint}` : label,
        'aria-pressed': kind === 'like' || kind === 'dislike' || kind === 'speak' ? 'false' : null }) as HTMLButtonElement
      b.innerHTML = actSvg(own?.icon ?? ACT[kind === 'dislike' ? 'like' : kind] ?? ACT.done)
      if (kind === 'speak' && !('speechSynthesis' in globalThis)) continue
      b.addEventListener('click', async () => {
        if (emit(kind, b.getAttribute('aria-pressed') === 'true' ? false : b.hasAttribute('aria-pressed') || undefined)) return
        if (kind === 'copy') {
          try { await navigator.clipboard.writeText(text) } catch { return }
          b.innerHTML = actSvg(ACT.done); b.classList.add('done')
          setTimeout(() => { b.innerHTML = actSvg(ACT.copy); b.classList.remove('done') }, 1500)
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
    this._uploading = list.map((f) => ({ name: f.name, preview: view(f) }))
    this._renderFiles()
    try {
      for (let i = 0; i < list.length; i++) {
        const att = await upload(list[i], this)
        const preview = this._uploading[0]?.preview
        if (preview) this._previews.set(att.id, preview)
        if (at === undefined) this._files.push(att); else this._files.splice(at + i, 0, att)
        this._uploading.shift()
        this._renderFiles()
      }
    } catch (e) {
      this.$.hint.textContent = `${this.t('error')} ${e instanceof Error ? e.message : String(e)}`
    }
    this._uploading = []
    this._renderFiles()
    this._syncSend()
  }

  /** A tile for an attachment: an image's thumbnail, or a document's name and type; × removes it from the message. */
  private _tile(name: string, preview: string | undefined, remove?: () => void, busy = false, edit?: number): HTMLElement {
    const ext = (name.match(/\.([a-z0-9]{1,5})$/i)?.[1] ?? '').toUpperCase()
    const tile = h('span', { class: `att${preview ? '' : ' doc'}${busy ? ' busy' : ''}`, part: 'attachment', title: name },
      preview ? h('button', { class: 'att-open', type: 'button', 'aria-label': name, onclick: (e: Event) => this._zoom(e.currentTarget as HTMLElement, edit === undefined ? undefined : (blob) => this._replaceFile(edit, blob, name)) }, h('img', { src: preview, alt: '' }))
        : [h('span', { class: 'att-name' }, name), ext ? h('span', { class: 'att-ext' }, ext) : null])
    if (remove) tile.append(h('button', { class: 'att-x', type: 'button', 'aria-label': `${this.t('remove')} ${name}`, onclick: remove }, '\u00d7'))
    return tile
  }

  /** The image, large, over the chat: × or Esc or a tap beside it closes it. */
  private _zoom(opener: HTMLElement, edit?: (image: Blob) => void): void {
    // the images sent with the same message page with \u2039 1 of 2 \u203a, \u2190 / \u2192 and a swipe; one in the composer stays alone
    const own = opener.closest('.att-row')
    const openers = own ? [...own.querySelectorAll<HTMLElement>('.att-open')] : [opener]
    const row = openers.map((b) => ({ src: b.querySelector('img')?.getAttribute('src') ?? '', name: b.getAttribute('aria-label') ?? '' }))
    let at = Math.max(0, openers.indexOf(opener))
    // a modal <dialog>: the browser puts it above everything on the page (no stacking context can cover it), Esc closes it
    const x = h('button', { class: 'zoom-x', type: 'button', 'aria-label': this.t('close') }); this._icon(x, 'close')
    const img = h('img', { src: row[at]?.src, alt: row[at]?.name }) as HTMLImageElement
    // the buttons sit on the picture's corner and the pager under it, not in the corners of the screen
    const fig = h('div', { class: 'zoom-fig' }, img, x)
    // beside the picture's top right corner when there is room (nothing covers it); on it otherwise (a phone)
    const place = (): void => { fig.classList.toggle('out', fig.getBoundingClientRect().right + 52 <= innerWidth) }
    img.addEventListener('load', place)
    addEventListener('resize', place)
    const view = h('dialog', { class: 'zoom', part: 'zoom', 'aria-label': row[at]?.name }, fig) as HTMLDialogElement
    let swiped = false
    if (row.length > 1) {
      const count = h('span', { class: 'zoom-n', 'aria-live': 'polite' })
      const step = (d: number) => {
        const b = h('button', { class: 'zoom-go', type: 'button', 'aria-label': this.t(d < 0 ? 'prevImage' : 'nextImage') })
        b.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d < 0 ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7'}"/></svg>`
        b.addEventListener('click', (e) => { e.stopPropagation(); show(at + d) })
        return b
      }
      const prev = step(-1), next = step(1)
      // like Photos: no wrap-around, the arrow at an end is dimmed
      const show = (i: number): void => {
        at = Math.max(0, Math.min(row.length - 1, i))
        img.src = row[at].src; img.alt = row[at].name; view.setAttribute('aria-label', row[at].name)
        count.textContent = this.t('nOfTotal', { n: at + 1, total: row.length })
        prev.disabled = at === 0; next.disabled = at === row.length - 1
      }
      fig.append(h('div', { class: 'zoom-pager', part: 'zoom-pager' }, prev, count, next))
      show(at)
      view.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight') { e.preventDefault(); show(at + 1) }
        if (e.key === 'ArrowLeft') { e.preventDefault(); show(at - 1) }
      })
      let x0 = 0
      view.addEventListener('pointerdown', (e) => { x0 = e.clientX })
      view.addEventListener('pointerup', (e) => { const dx = e.clientX - x0; if (Math.abs(dx) > 40) { swiped = true; show(at + (dx < 0 ? 1 : -1)) } })
    }
    const close = (): void => { view.close() }
    x.addEventListener('click', close)
    view.addEventListener('click', (e) => { if (swiped) { swiped = false; return } if (e.target === view) close() })   // a tap beside the picture
    view.addEventListener('close', () => { view.remove(); removeEventListener('resize', place) })
    // an image still in the composer can be marked up (the editor loads now): Save puts the marked-up copy in its place
    if (edit) {
      const pencil = h('button', { class: 'zoom-x zoom-edit', type: 'button', 'aria-label': this.t('markup') })
      pencil.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20l4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20zM14 7l3 3"/></svg>'
      pencil.addEventListener('click', (e) => {
        e.stopPropagation()
        void loadEditor().then((open) => {
          img.hidden = true; x.hidden = true; pencil.hidden = true
          open({ src: row[at].src, name: row[at].name, mount: view, t: (k) => this.t(k), onSave: (blob) => { edit(blob); close() }, onClose: close })
        }).catch(() => { pencil.hidden = true })   // no editor file next to the script: the view stays
      })
      fig.append(pencil)
    }
    this.$.wrap.append(view)
    if (typeof view.showModal === 'function') view.showModal(); else view.setAttribute('open', '')
    requestAnimationFrame(place)
    x.focus({ preventScroll: true })
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
    // only a tile that was not there before plays its entrance: removing or adding one leaves the others still
    const before = new Set([...this.$.files.querySelectorAll<HTMLElement>('.att')].map((t) => t.title))
    queueMicrotask(() => this.$.files.querySelectorAll<HTMLElement>('.att').forEach((t) => { if (!before.has(t.title)) t.classList.add('att-new') }))
    this.$.files.replaceChildren(
      ...this._files.map((f, i) => this._tile(f.filename, this._previews.get(f.id), () => {
        this._files.splice(i, 1); this._renderFiles(); this._syncSend()
        if (finePointer()) (this.$.input as HTMLTextAreaElement).focus({ preventScroll: true })   // the composer keeps its focus: no border flash
      }, false, i)),
      ...this._uploading.map((u) => this._tile(u.name, u.preview, undefined, true)))
    this.$.files.hidden = !this._files.length && !this._uploading.length
    requestAnimationFrame(() => this._fadeFiles())
  }

  /** Thumbnails of attached images (object URLs) by attachment id, and the files still uploading. */
  private _previews = new Map<string, string>()
  private _uploading: { name: string; preview?: string }[] = []

  private _showDots(on: boolean): void {
    if (on && !this._dots) {
      const dots = h('div', { class: 'msg ai wait', 'aria-label': this.t('working') }, h('span', { class: 'dots' }, h('i'), h('i'), h('i')))
      this._dots = dots
      this.$.log.appendChild(dots)
      setTimeout(() => { if (this._dots === dots) dots.appendChild(h('span', { class: 'slow', role: 'status' }, this.t('slow'))) }, SLOW_MS)
      this._scroll()
    } else if (!on && this._dots) {
      this._dots.remove()
      this._dots = null
    }
  }

  private _clearQuick(): void { this._quick?.remove(); this._quick = null; this._suggestions = []; this._applies = [] }

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
    this._quick = this._append(h('div', { class: 'quick' }, ...(own ? [own] : [h('div', { class: 'chips' }, chips), err])))
    this._quick.hidden = !this._opts.quickReplies
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
    if (r.messages?.length) {
      this._messages = r.messages.filter((m) => m.role !== 'activity')   // cards are shown, not sent back as history
      this.$.log.replaceChildren()
      this._stick = true
      for (const m of r.messages) {
        if (m.role === 'user' && m.content) this._userBubble(m.content)
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
    if (aborted) { this.notice(this.t('stopped')); return }
    if (failed) {
      this.dispatchEvent(new CustomEvent('agui:error', { detail: failed }))
      const again = () => { el.remove(); if (this._lastRun) void this._run(this._lastRun) }
      const retry = h('button', { class: 'btn sec', type: 'button', onclick: again }, this.t('retry'))
      const own = this.renderSlot('error', { message: failed, kind: errorKind(failed), text: this.t(errorKind(failed)), retry: again })
      const el = this._append(h('div', { class: 'error', role: 'alert' }, ...(own ? [own] : [h('span', { title: failed }, this.t(errorKind(failed))), retry])))
      return
    }
    this.dispatchEvent(new CustomEvent('agui:run-end', { detail: { threadId: this._thread } }))
    if (this._pendingCalls.length && !this._interrupted) await this._runFrontendTools()
    else if (!this._interrupted) { const thread = this._thread; void this._typing.then(() => { if (this._thread === thread) this._renderQuick() }) }   // quick replies last
  }

  private _setBusy(on: boolean): void {
    this._busy = on
    this.toggleAttribute('busy', on)
    this.$.jump?.classList.toggle('busy', on)   // "•••" in the jump button: it is still answering below
    this._syncSend()
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
      if (p?.parent_id) this._addSubStep(p.parent_id, p.name ?? '')
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

  private _ensureSteps(): StepsItem {
    if (this._steps) return this._steps
    const list = h('ul')
    const toggle = h('button', { type: 'button', 'aria-expanded': 'true' }, this.t('working')) as HTMLButtonElement
    const el = h('div', { class: 'steps openlist quiet', part: 'steps' }, toggle, list)
    toggle.addEventListener('click', () => {
      const closed = el.classList.toggle('collapsed')
      el.classList.toggle('openlist', !closed)
      toggle.setAttribute('aria-expanded', String(!closed))
    })
    el.hidden = true   // shown with the first step that is not a routine look-up
    this._steps = { el, list, toggle, steps: new Map(), count: 0 }
    this._append(el)
    return this._steps
  }

  private _addStep(id: string, name: string, label?: string): void {
    const s = this._ensureSteps()
    const li = h('li', { class: 'run' }, h('span', { class: 'mark' }), h('span', null, label ?? this._label(name)))
    s.steps.set(id, li)
    s.count++
    if (!this._plugins.some((p) => p.quietSteps?.includes(name))) {   // a real step: the list shows
      s.el.classList.remove('quiet')
      s.el.hidden = !this._opts.toolSteps
    }
    s.list.appendChild(li)
    this._scroll()
  }

  private _addSubStep(parent: string, name: string): void {
    const li = this._steps?.steps.get(parent)
    if (!li) return
    let ul = li.querySelector('ul')
    if (!ul) { ul = h('ul'); li.classList.add('has-sub'); li.appendChild(ul) }
    ul.querySelectorAll('li.run').forEach((x) => x.classList.replace('run', 'ok'))
    ul.appendChild(h('li', { class: 'sub run' }, h('span', { class: 'mark' }), h('span', null, this._label(name))))
  }

  private _doneStep(id: string): void {
    const li = this._steps?.steps.get(id)
    if (!li) return
    li.classList.replace('run', 'ok')
    li.querySelectorAll('li.run').forEach((x) => x.classList.replace('run', 'ok'))
  }

  private _finishSteps(failed: boolean): void {
    const s = this._steps
    if (!s) return
    s.el.querySelectorAll('li.run').forEach((x) => x.classList.replace('run', failed ? 'fail' : 'ok'))
    s.toggle.textContent = this.t('steps', { n: s.count })
    s.el.classList.add('collapsed')
    s.el.classList.remove('openlist')
    s.toggle.setAttribute('aria-expanded', 'false')
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

/**
 * The formguide plugin: sends the form with every run, applies "look here" directives, and renders
 * formguide's cards (field changes, questions, upload requests, confirmations).
 *
 *   chat.use(formguide({
 *     getState: () => ({ config, jsx_hash, form_id, ui }),      // the form as your backend last built it
 *     applyChanges: (changes) => formBackend.apply(changes),     // -> the new config
 *   }))
 */
import type { AguiEvent, ChatApi, Interrupt, Plugin, Restored, RunAgentInput } from '../types'
import { askCard, confirmCard, fieldCard, uploadCard } from './cards'
import { FG_STRINGS, TOOL_LABELS } from './i18n'

export interface FormState { config: { props?: Record<string, any>; state?: Record<string, unknown> }; jsx_hash: string; form_id?: string; ui?: unknown; [k: string]: unknown } // eslint-disable-line @typescript-eslint/no-explicit-any

export interface Directive { type: 'focus'; target: string; reveal: ({ type: 'tab'; tabs: string; tab: string } | { type: 'accordion'; name: string })[]; hint: string }

export interface FieldCardFlags { select: boolean; diff: boolean; reason: boolean; edit: boolean; jump: boolean; undo: boolean }

export interface FormguideOptions {
  /** The current form: {config, jsx_hash, form_id, ui}. Sent as the run's `state`. */
  getState: () => FormState | Promise<FormState>
  /** Send {name: value} to your form backend the same way user input goes; return the new config. */
  applyChanges: (changes: Record<string, unknown>) => Promise<FormState['config']> | FormState['config']
  /** Put the previous values back (Undo). Default: applyChanges(previous). */
  revertChanges?: (previous: Record<string, unknown>) => Promise<unknown> | unknown
  /** "Look here": open these tabs and accordions, scroll to the field, highlight it. */
  onDirective?: (d: Directive) => void
  /** Where formguide's router is mounted (threads, attachments). Default: the run URL without /run. */
  baseUrl?: string
  /** Field-change card features; all on by default. */
  fieldCard?: Partial<FieldCardFlags>
  /** How long Undo stays available after a card is applied, in seconds. */
  undoSeconds?: number
  /** Show "Preparing a question" etc. as steps although the card itself follows. Default false. */
  cardSteps?: boolean
}

export interface Ctx extends FormguideOptions { base: (chat: ChatApi) => string; flags: FieldCardFlags }

/** The default "look here" without a host callback: scroll to [data-name=target] and flash it. */
export function defaultDirective(d: Directive): void {
  const el = document.querySelector<HTMLElement>(`[data-name="${CSS.escape(d.target)}"]`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.animate?.([{ boxShadow: '0 0 0 0 rgba(0,113,227,.55)' }, { boxShadow: '0 0 0 8px rgba(0,113,227,0)' }], { duration: 900, iterations: 2 })
}

/** A pending card or question from GET /threads/{id} (a transcript entry) -> an interrupt payload. */
export function entryToInterrupt(e: Record<string, any> | null | undefined): Interrupt | null { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!e) return null
  const { id, kind, ts: _ts, status: _st, ...rest } = e
  void _ts; void _st
  const type = { card: 'set_fields', question: 'ask', upload: 'upload', confirm: 'confirm' }[kind as string]
  return type ? { type, card_id: id, ...rest } : null
}

export function formguide(opts: FormguideOptions): Plugin {
  const flags: FieldCardFlags = { select: true, diff: true, reason: true, edit: true, jump: true, undo: true, ...(opts.fieldCard ?? {}) }
  const ctx: Ctx = {
    ...opts, flags,
    base: (chat) => (opts.baseUrl ?? chat.options.url.replace(/\/run\/?$/, '')).replace(/\/$/, ''),
  }
  const labels: Record<string, Record<string, string>> = {}
  for (const [lang, m] of Object.entries(TOOL_LABELS)) for (const [tool, label] of Object.entries(m)) (labels[tool] ??= {})[lang] = label
  // the card that follows already shows what these tools did: no separate step for them
  const toolLabels: Record<string, Record<string, string> | string> = { ...labels }
  if (!opts.cardSteps) for (const t of ['propose_changes', 'ask_user', 'request_file', 'confirm_action']) toolLabels[t] = ''
  return {
    name: 'formguide',
    i18n: FG_STRINGS,
    toolLabels,
    renderers: {
      set_fields: (it, c) => fieldCard(it, c, ctx),
      ask: (it, c) => askCard(it, c, ctx),
      upload: (it, c) => uploadCard(it, c, ctx),
      confirm: (it, c) => confirmCard(it, c),
    },
    async beforeRun(input: RunAgentInput, chat: ChatApi) {
      const st = await opts.getState()
      input.state = chat.attachments.length ? { ...st, attachments: chat.attachments } : st
    },
    attach: {
      accept: '.pdf,.png,.jpg,.jpeg,.webp,.gif,.txt,.md',
      async upload(file: File, chat: ChatApi) {
        const body = new FormData()
        body.append('thread_id', chat.threadId)
        body.append('file', file)
        const r = await fetch(`${ctx.base(chat)}/attachments`, { method: 'POST', body })
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? r.statusText)
        return r.json()
      },
    },
    onEvent(ev: AguiEvent) {
      if (ev.type === 'CUSTOM' && ev.name === 'ui_directive') {
        (opts.onDirective ?? defaultDirective)(ev.value as Directive)
        return true
      }
      return false
    },
    async restore(threadId: string, chat: ChatApi): Promise<Restored | null> {
      const st = await opts.getState()
      const q = new URLSearchParams({ format: 'agui', ...(st.form_id ? { form_id: st.form_id } : {}) })
      const r = await fetch(`${ctx.base(chat)}/threads/${encodeURIComponent(threadId)}?${q}`)
      if (!r.ok) return null
      const d = await r.json()
      return { messages: d.messages ?? [], interrupt: entryToInterrupt(d.pending_card), starters: d.starters ?? [] }
    },
  }
}

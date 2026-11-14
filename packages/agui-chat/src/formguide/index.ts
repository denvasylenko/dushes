/**
 * The formguide plugin: sends the form with every run, applies "look here" directives, and renders
 * formguide's cards (field changes, questions, upload requests, confirmations).
 *
 *   chat.use(formguide({
 *     getState: () => ({ config, jsx_hash, form_id, ui }),      // the form as your backend last built it
 *     applyChanges: (changes) => formBackend.apply(changes),     // -> the new config
 *   }))
 */
import { blocksCard, preloadBlocks, withBlocks } from './blocks-later'
import { h } from '../dom'
import type { AguiEvent, ChatApi, Interrupt, Plugin, RendererContext, Restored, RunAgentInput } from '../types'
import { appliedLine, askCard, confirmCard, fieldCard, undoLine, uploadCard } from './cards'
import { CAPABILITIES, receiptEl, reviewCard, sourcesEl } from './pickers'
import { FG_STRINGS, TOOL_LABELS } from './i18n'
import { lookAt, ring } from './hint'

export { schemaForm, normOption } from './schema'
export { calendar, dateField, timeGrid, isoOf } from './calendar'
export type { FormSchema, FieldSchema, SectionSchema, FormAccess, SchemaBridge, Option } from './schema'

export interface FormState { config: { props?: Record<string, any>; state?: Record<string, unknown> }; jsx_hash: string; form_id?: string; ui?: unknown; [k: string]: unknown } // eslint-disable-line @typescript-eslint/no-explicit-any

export interface Directive {
  type: 'focus'; target: string; reveal: ({ type: 'tab'; tabs: string; tab: string } | { type: 'accordion'; name: string })[]; hint: string
  /** More fields to ring with the target (the required fields of a section), all visible once `reveal` is open. */
  also?: string[]
}

export interface FieldCardFlags { select: boolean; diff: boolean; reason: boolean; edit: boolean; jump: boolean; undo: boolean }

export interface FormguideOptions {
  /** The current form: {config, jsx_hash, form_id, ui}. Sent as the run's `state`. */
  getState: () => FormState | Promise<FormState>
  /** Send {name: value} to your form backend the same way user input goes; return the new config. */
  applyChanges: (changes: Record<string, unknown>) => Promise<FormState['config']> | FormState['config']
  /** A button of a card from blocks was tapped: return true when your code handled it (saved a step, applied a
   *  style, sent a booking to your server), and the chat does nothing more: no message, no answer. Redraw the card
   *  with chat.updateCard(card.card_id, {blocks}) if it should change. */
  onAction?: (card: Record<string, unknown>, action: { id: string; label: string; values: Record<string, unknown> }, chat: ChatApi) => boolean | Promise<boolean>
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
  /** A live line under a range question, e.g. the monthly payment for a term: (field, value) -> text. */
  preview?: (field: string, value: number) => string | Promise<string>
  /** Free time slots for a time question: (field, date or null) -> ["10:00", ...]. */
  getSlots?: (field: string, date: string | null) => string[] | Promise<string[]>
  /** Address suggestions as the user types: (field, query) -> [{label, detail?, value?}]. */
  lookupAddress?: (field: string, query: string) => { label: string; detail?: string; value?: unknown }[] | Promise<{ label: string; detail?: string; value?: unknown }[]>
  /** The thumbs rating after a confirmed action; default: POST {base}/feedback. */
  onFeedback?: (value: 1 | -1) => void | Promise<void>
  /** Cards and variants this app does not want, e.g. ['review', 'upload', 'ask.range']. They are left out of
   * the capabilities the plugin announces, so the server never sends them: a whole card ('upload', 'review',
   * 'confirm', 'ask') also takes its tool away from the model; a variant ('ask.range') falls back to the
   * plain card. Field-change cards cannot be excluded. */
  exclude?: string[]
  /** The page's current W3C trace context, e.g. () => otel.propagation header: sent with every run as
   * forwardedProps.traceparent (and tracestate), so the server's turn span joins the page's trace. */
  traceparent?: () => string | { traceparent: string; tracestate?: string } | undefined | null
}

/** The cards every formguide client draws, besides the variants in CAPABILITIES. */
const BASE_CARDS = ['ask', 'upload', 'confirm', 'review', 'blocks', 'picker']

/** What this client announces: the base cards and variants, minus `exclude` (a card takes its variants along). */
export function capabilitiesFor(exclude: string[] = []): string[] {
  const out = [...new Set([...BASE_CARDS, ...CAPABILITIES])]
  return out.filter((c) => !exclude.some((x) => c === x || c.startsWith(`${x}.`)))
}

export interface Ctx extends FormguideOptions { base: (chat: ChatApi) => string; flags: FieldCardFlags }

/** The default "look here" without a host callback: scroll to [data-name=target] (or an input with that
 * name), focus it, ring it and show the agent's hint under it. Tabs and accordions are the host's: pass
 * onDirective to open them first. */
export function defaultDirective(d: Directive): void {
  lookAt(d.target, d.hint)
  for (const n of d.also ?? []) ring(n)
}

/** A pending card or question from GET /threads/{id} (a transcript entry) -> an interrupt payload. */
export function entryToInterrupt(e: Record<string, any> | null | undefined): Interrupt | null { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!e) return null
  const { id, kind, ts: _ts, status: _st, ...rest } = e
  void _ts; void _st
  const type = { card: 'set_fields', question: 'ask', upload: 'upload', confirm: 'confirm', review: 'review' }[kind as string]
  return type ? { type, card_id: id, ...rest } : null
}

export function formguide(opts: FormguideOptions): Plugin {
  /** The host's onAction for a card's buttons (true = handled: the chat does nothing more). */
  const act = (card: Record<string, unknown>, chat: ChatApi) => opts.onAction
    ? (id: string, label: string, values: Record<string, unknown>) => Promise.resolve(opts.onAction!(card, { id, label, values }, chat))
    : undefined
  const flags: FieldCardFlags = { select: true, diff: true, reason: true, edit: true, jump: true, undo: true, ...(opts.fieldCard ?? {}) }
  let host: HTMLElement | null = null   // the chat element, for the agui:applied event
  const told = (changes: Record<string, unknown>, undo = false) => host?.dispatchEvent(new CustomEvent('agui:applied',
    { detail: { fields: Object.keys(changes), values: changes, undo }, bubbles: true, composed: true }))
  const ctx: Ctx = {
    ...opts, flags,
    applyChanges: async (changes) => { const cfg = await opts.applyChanges(changes); told(changes); return cfg },
    revertChanges: async (previous) => { const r = await (opts.revertChanges ?? opts.applyChanges)(previous); told(previous, true); return r },
    onDirective: opts.onDirective ?? defaultDirective,   // cards show the field they filled, with or without a host callback
    base: (chat) => (opts.baseUrl ?? chat.options.url.replace(/\/run\/?$/, '')).replace(/\/$/, ''),
  }
  const labels: Record<string, Record<string, string>> = {}
  for (const [lang, m] of Object.entries(TOOL_LABELS)) for (const [tool, label] of Object.entries(m)) (labels[tool] ??= {})[lang] = label
  // the card that follows already shows what these tools did: no separate step for them
  const toolLabels: Record<string, Record<string, string> | string> = { ...labels }
  if (!opts.cardSteps) for (const t of ['propose_changes', 'ask_user', 'request_file', 'confirm_action', 'show_*']) toolLabels[t] = ''
  const caps = capabilitiesFor(opts.exclude)
  return {
    name: 'formguide',
    i18n: FG_STRINGS,
    toolLabels,
    // looking at the form and showing a field are routine (the form shows the latter): no "Steps: 1" for them
    quietSteps: ['get_outline', 'get_fields', 'get_field', 'search_fields', 'get_options', 'focus_field'],
    renderers: {
      set_fields: (it, c) => { host = c.chat.host; return fieldCard(it, c, ctx) },
      ask: (it, c) => { host = c.chat.host; return askCard(it, c, ctx) },
      upload: (it, c) => uploadCard(it, c, ctx),
      confirm: (it, c) => confirmCard(it, c, ctx),
      review: (it, c) => reviewCard(it, c, ctx, (line, fields) => undoLine(line, c, ctx, fields)),
      // cards composed from blocks (formguide.yaml `cards:`, or showCard); a button's `fills` go through the form
      // (the one-script build loads the blocks with the first such card: its element is shown at once and filled then)
      blocks: (it, c) => { host = c.chat.host; const box = h('div', null); return withBlocks(box, c, (b) => b.blocksRenderer(it, c, {
        apply: (ch) => Promise.resolve(ctx.applyChanges(ch)), state: async () => await ctx.getState(),
        undo: (line, fields) => undoLine(line, c, ctx, fields) }, act(it, c.chat), box)) },
      // a picker (day, time, people, contacts, one button): the same blocks, laid out from its groups and fields
      picker: (it, c) => { host = c.chat.host; const box = h('div', null); return withBlocks(box, c, (b) => b.blocksRenderer(it, c, undefined, act(it, c.chat), box)) },
    },
    /** An action chip: fill its fields at once (Undo on the line). A chip whose fields changed since is out of date. */
    async applySuggestion(raw: unknown[], chat: ChatApi) {
      const changes = raw as { name: string; label?: string; value: unknown; previous?: unknown }[]
      const now = (await opts.getState()).config?.state ?? {}
      const same = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null)
      if (changes.some((x) => x.name in now && !same(now[x.name], x.previous))) throw new Error(chat.t('stale'))
      host = chat.host
      await ctx.applyChanges(Object.fromEntries(changes.map((x) => [x.name, x.value])))
      const last = changes[changes.length - 1] as { name: string; reveal?: Directive['reveal'] }
      ctx.onDirective!({ type: 'focus', target: last.name, reveal: last.reveal ?? [], hint: '' })   // show what the chip filled
      const c = { chat, t: chat.t.bind(chat), flags: {}, resolve: () => {} } as unknown as RendererContext
      return appliedLine(c, ctx, changes.map((x) => ({ name: x.name, label: x.label ?? x.name, previous: x.previous ?? null })))
    },
    async beforeRun(input: RunAgentInput, chat: ChatApi) {
      if (caps.some((x) => x === 'blocks' || x === 'picker')) void preloadBlocks().catch(() => {})   // so the first card arrives drawn
      const st = await opts.getState()
      input.state = chat.attachments.length ? { ...st, attachments: chat.attachments } : st
      // what this client can draw: the server sends only these card variants
      const tp = opts.traceparent?.()
      const trace = typeof tp === 'string' ? { traceparent: tp } : tp ?? {}
      input.forwardedProps = { ...(input.forwardedProps ?? {}), capabilities: caps, ...trace }
    },
    attach: {
      accept: '.pdf,.png,.jpg,.jpeg,.webp,.gif,.txt,.md',
      async upload(file: File, chat: ChatApi) {
        const body = new FormData()
        body.append('thread_id', chat.threadId)
        body.append('file', file)
        const r = await chat.request('attachments', `${ctx.base(chat)}/attachments`, { method: 'POST', body })
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? r.statusText)
        return r.json()
      },
    },
    onEvent(ev: AguiEvent, chat: ChatApi) {
      if (ev.type !== 'CUSTOM') return false
      if (ev.name === 'card') {   // a display card (route, share, "3 steps left"): shown, nobody waits for it
        host = chat.host
        const v = { ...(ev.value ?? {}) as Record<string, unknown> }
        const id = String(v.card_id ?? `card-${Math.random().toString(36).slice(2, 10)}`)
        v.card_id = id
        const rc = { chat, t: chat.t.bind(chat), resolve: () => {}, flags: {}, restored: false }
        const draw = (p: Record<string, unknown>) => {
          const el = blocksCard(p, rc, null, act(p, chat))
          el.classList.add('card'); el.setAttribute('part', `card card-blocks blocks-${String(p.name ?? 'card')}`)
          el.dataset.cardId = id
          return el
        }
        chat.registerCard(id, v, draw)   // chat.updateCard(id, {blocks}) redraws it in place
        chat.append(draw(v))
        return true
      }
      if (ev.name === 'ui_directive') {
        ctx.onDirective!(ev.value as Directive)
        return true
      }
      if (ev.name === 'sources') {   // chips under the answer: where it came from
        const items = (ev.value as { items?: { title: string; section?: string; quote?: string }[] })?.items ?? []
        if (items.length) chat.append(chat.renderSlot('sources', items) ?? sourcesEl(items))   // render.sources replaces the chips
        return true
      }
      if (ev.name === 'receipt') {   // the confirmed card turns into its receipt
        const r = ev.value as { card_id?: string; title?: string; number?: string; eta?: string }
        const card = chat.host.shadowRoot?.querySelector(`[data-card-id="${CSS.escape(String(r?.card_id ?? ''))}"]`)
        const line = card?.querySelector('.ok-line')
        const el = receiptEl({ t: chat.t.bind(chat) }, r ?? {})
        if (line) line.replaceWith(el); else chat.append(el)
        return true
      }
      return false
    },
    /** The server's turn runs on after the connection closes (a reload must not lose it): Stop ends it there. */
    onStop(chat: ChatApi) {
      void chat.request('stop', `${ctx.base(chat)}/stop`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: chat.threadId }) }).catch(() => {})
    },
    async restore(threadId: string, chat: ChatApi): Promise<Restored | null> {
      const st = await opts.getState()
      const q = new URLSearchParams({ format: 'agui', ...(st.form_id ? { form_id: st.form_id } : {}) })
      const r = await chat.request('thread', `${ctx.base(chat)}/threads/${encodeURIComponent(threadId)}?${q}`)
      if (!r.ok) return null
      const d = await r.json()
      return { messages: d.messages ?? [], interrupt: entryToInterrupt(d.pending_card), starters: d.starters ?? [], running: !!d.running }
    },
  }
}

/** The blocks, for a card renderer of your own (chat.renderers.set): compose with the same parts and theme.
 *  `loadBlocks()` resolves once they are here (at once with a bundler; agui-chat.blocks.js in the one-script build). */
export { blocksCard, preloadBlocks as loadBlocks }
export { hoursText } from './blocks-base'
export type { Block, OnAction } from './blocks'

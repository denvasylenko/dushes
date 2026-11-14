/**
 * Richer looks for formguide's cards, chosen from the data the server sends (the model gets no new tools):
 * options with details, comparisons, search in long lists, day strips, time slots, ranges, addresses,
 * several short fields, the form review, sources, receipts and the thumbs rating.
 * Each view falls back to the plain controls when its data or the host's callback is missing.
 */
import { h, numberBox } from '../dom'
import type { ChatApi, Interrupt, RendererContext } from '../types'
import type { Ctx } from './index'
import { dateField } from './calendar'
import { isPlainNumber } from './plain'
import { blocksNow, loadBlocks } from '#blocks-loader'

export interface Opt { id: string; label: string; value?: unknown; description?: string; attrs?: Record<string, string> }

/** The variants this plugin renders, sent as forwardedProps.capabilities. */
export const CAPABILITIES = ['ask.details', 'ask.compare', 'ask.search', 'ask.date', 'ask.slots', 'ask.range', 'ask.multi',
  'ask.address', 'set.consent', 'set.issues', 'set.document', 'review', 'sources', 'confirm.receipt', 'upload.camera', 'feedback']

const SEARCH_ABOVE = 12
const FIRST_SHOWN = 5

// ---------------------------------------------------------------- values

/** A value for a card row, formatted by the field's role. Without a role: large plain numbers only.
 * Yes/no fields arrive as the server's language-neutral marks (\u2713 / \u2717): shown as words. */
export function formatValue(display: unknown, kind: string | undefined, lang: string, words?: { yes: string; no: string }, name?: string): string {
  const v = String(display ?? '')
  if (/^-?\d+(\.\d+)?$/.test(v) && isPlainNumber(name)) return v   // a year or an id, as written
  if (words && (kind === 'bool' || v === '\u2713' || v === '\u2717' || v === '\u2715')) {
    if (v === '\u2713' || v === 'true') return words.yes
    if (v === '\u2717' || v === '\u2715' || v === 'false') return words.no
  }
  try {
    // separators from five digits on (15,000; 1,500,000): a four-digit year or id never gets one, whatever its name
    if (kind === 'number' && /^-?\d+(\.\d+)?$/.test(v)) return new Intl.NumberFormat(lang || undefined, { useGrouping: 'min2' } as unknown as Intl.NumberFormatOptions).format(Number(v))
    if (kind === 'date' && /^\d{4}-\d{2}-\d{2}$/.test(v)) {
      return new Intl.DateTimeFormat(lang || undefined, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
        .format(new Date(`${v}T00:00:00Z`))
    }
    if (!kind && /^-?\d{5,}(\.\d+)?$/.test(v)) return new Intl.NumberFormat(lang || undefined).format(Number(v))
  } catch { /* keep as is */ }
  return v
}

// ---------------------------------------------------------------- options

/** How a list of options is drawn: comparison, two-line options, a searchable list or chips. */
export function optionsLook(options: Opt[]): 'compare' | 'details' | 'search' | 'chips' {
  if (options.length > SEARCH_ABOVE) return 'search'
  const keys = (o: Opt) => Object.keys(o.attrs ?? {}).sort().join('|')
  if (options.length >= 2 && options.length <= 3 && keys(options[0]) && options.every((o) => keys(o) === keys(options[0]))) return 'compare'
  if (options.some((o) => o.description)) return 'details'
  return 'chips'
}

/** The option buttons for a question; `onPick` gets the option, `chipFor` builds today's chip. */
export function optionsView(it: Interrupt, c: RendererContext, options: Opt[], onPick: (o: Opt, b: HTMLButtonElement) => void,
  chipFor: (o: Opt, i: number) => HTMLButtonElement): { el: HTMLElement | null; buttons: HTMLButtonElement[] } {
  if (!options.length) return { el: null, buttons: [] }
  const look = optionsLook(options)
  const numeric = options.some((o) => /\d/.test(o.label))   // hints 1-9 would read as part of the answer
  if (look === 'chips') {
    const buttons = options.map(chipFor)
    return { el: h('div', { class: 'chips' }, buttons), buttons }
  }
  const optButton = (o: Opt, i: number) => {
    const b = h('button', { class: 'opt', part: 'chip', type: 'button' },
      i < 9 && look !== 'search' && !numeric ? h('kbd', null, String(i + 1)) : null,
      h('b', null, o.label), o.description ? h('span', { class: 'muted' }, o.description) : null) as HTMLButtonElement
    b.addEventListener('click', () => onPick(o, b))
    return b
  }
  if (look === 'compare') {
    const keys = Object.keys(options[0].attrs ?? {})
    const buttons = options.map((o, i) => {
      const b = h('button', { class: `opt cmp-col${it.recommended === o.id ? ' rec' : ''}`, part: 'chip', type: 'button' },
        it.recommended === o.id ? h('span', { class: 'tag' }, c.t('recommended')) : null,
        h('b', null, o.label),
        keys.map((k) => h('span', { class: 'cmp-v' }, h('span', { class: 'muted' }, k), h('span', null, o.attrs![k]))),
        i < 9 && !numeric ? h('kbd', null, String(i + 1)) : null) as HTMLButtonElement
      b.addEventListener('click', () => onPick(o, b))
      return b
    })
    const note = it.sources?.length ? h('div', { class: 'muted note' }, c.t('fromDocs')) : null
    return { el: h('div', null, h('div', { class: 'cmp' }, buttons), note), buttons }
  }
  if (look === 'details') {
    const buttons = options.map(optButton)
    return { el: h('div', { class: 'opts' }, buttons), buttons }
  }
  // search: the suggested (or first) options, the rest as you type
  const suggested: string[] = Array.isArray(it.suggested) ? it.suggested.map(String) : []
  const first = suggested.length ? options.filter((o) => suggested.includes(o.id)) : options.slice(0, FIRST_SHOWN)
  const list = h('div', { class: 'opts' })
  const empty = h('div', { class: 'muted', hidden: true }, c.t('noMatch'))
  const all = options.map(optButton)
  const show = (q: string) => {
    const s = q.trim().toLowerCase()
    const shown = s ? options.filter((o) => `${o.label} ${o.description ?? ''}`.toLowerCase().includes(s)).slice(0, 30) : first
    list.replaceChildren(...shown.map((o) => all[options.indexOf(o)]))
    empty.hidden = shown.length > 0
  }
  const box = h('input', { class: 'text-in search', type: 'search', placeholder: c.t('searchN', { n: options.length }),
    'aria-label': c.t('searchN', { n: options.length }), oninput: (e: Event) => show((e.target as HTMLInputElement).value) }) as HTMLInputElement
  show('')
  return { el: h('div', null, box, list, empty), buttons: [] }
}

// ---------------------------------------------------------------- typed answers

type Commit = (value: unknown, label: string) => void
const TYPED = ['date', 'time', 'number', 'address']

/** The richer control for a typed question (typed.ts, in the blocks script, here once a run has started), or null for
 *  the plain input. Not here yet (a card restored after a reload): an empty slot, filled when the script arrives. */
export function typedView(it: Interrupt, c: RendererContext, ctx: Ctx | undefined, commit: Commit, input: HTMLInputElement | null): HTMLElement | null {
  if (!TYPED.includes(String(it.input?.type))) return null
  const now = blocksNow()
  if (now) return now.typedView(it, c, ctx, commit, input)
  const plain = (): void => { slot.remove(); if (input) input.hidden = false }
  if (input && it.input?.type !== 'address') input.hidden = true
  const slot = h('div', { class: 'typed-slot' })
  void loadBlocks().then((b) => { const v = b.typedView(it, c, ctx, commit, input); if (v) slot.replaceWith(v); else plain() }).catch(plain)
  return slot
}

// ---------------------------------------------------------------- several short fields

const INPUT_TYPES: Record<string, string> = { date: 'date', time: 'time', number: 'number', text: 'text' }

/** 2-3 short fields in one card ("Your name, as in the passport"): fills them at once, with Undo. */
export function fieldsView(it: Interrupt, c: RendererContext, ctx: Ctx | undefined,
  done: (values: Record<string, unknown>, labels: string) => Promise<void>): HTMLElement {
  const fields: { name: string; label?: string; input?: { type?: string }; required?: boolean }[] = it.fields ?? []
  const inputs = fields.map((f) => h('input', { class: 'text-in', type: INPUT_TYPES[f.input?.type ?? 'text'] ?? 'text',
    'aria-label': f.label ?? f.name, oninput: () => sync() }) as HTMLInputElement)   // the label above says what it is
  const btn = h('button', { class: 'btn pri', type: 'button' }) as HTMLButtonElement
  const filled = () => inputs.filter((i) => i.value.trim()).length
  const missing = () => fields.filter((f, i) => f.required !== false && !inputs[i].value.trim()).length
  const sync = () => {
    const n = filled()
    btn.textContent = missing() ? c.t('fillRequired', { n: missing() }) : c.t('fillFields', { n, fields: c.t(`field_${new Intl.PluralRules(c.chat.lang).select(n)}`) })
    btn.disabled = missing() > 0 || n === 0
  }
  btn.addEventListener('click', () => {
    const values: Record<string, unknown> = {}
    fields.forEach((f, i) => {
      const v = inputs[i].value.trim()
      if (v) values[f.name] = f.input?.type === 'number' ? Number(v) : v
    })
    void done(values, fields.filter((f) => f.name in values).map((f) => `${f.label ?? f.name}: ${values[f.name]}`).join(', '))
  })
  inputs.forEach((i, n) => i.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return
    e.preventDefault()
    if (n < inputs.length - 1) inputs[n + 1].focus(); else btn.click()
  }))
  sync()
  void ctx
  // a label above each input: date and time inputs show no placeholder
  return h('div', { class: 'fields' }, fields.map((f, i) => h('label', { class: 'fld' }, h('span', { class: 'muted' }, f.label ?? f.name),
    inputs[i].type === 'number' ? numberBox(inputs[i])
      : inputs[i].type === 'date' ? dateField({ lang: c.chat.lang, label: f.label ?? f.name, t: c.t, limits: { min: (f.input as { min?: string })?.min, max: (f.input as { max?: string })?.max },
          onChange: (d) => { inputs[i].value = d; inputs[i].dispatchEvent(new Event('input')) } }).el
        : inputs[i])),
    h('div', { class: 'acts' }, btn))
}

// ---------------------------------------------------------------- review

type Undo = (line: HTMLElement, fields: { name: string; label: string; previous: unknown }[]) => void

/** The review card (review.ts) ships with the card blocks, here once a run has started; not here yet (restored
 *  after a reload), a quiet box of its place is filled in place when the file arrives. */
export function reviewCard(it: Interrupt, c: RendererContext, ctx: Ctx, undoFor: Undo): HTMLElement {
  const now = blocksNow()
  if (now) return now.reviewCard(it, c, ctx, undoFor)
  const box = h('div', { class: 'rev', 'aria-busy': 'true' })
  void loadBlocks().then((b) => box.replaceWith(b.reviewCard(it, c, ctx, undoFor))).catch(() => {})
  return box
}

// ---------------------------------------------------------------- sources, receipt, feedback

/** Chips under an answer: where it came from. */
export function sourcesEl(items: { title: string; section?: string; quote?: string }[]): HTMLElement {
  return h('div', { class: 'chips srcs', part: 'sources' }, items.map((s) => {
    const label = `${s.title}${s.section ? ` › ${s.section}` : ''}`
    const chip = h('button', { class: 'chip src-chip', type: 'button', title: s.quote ?? label, 'aria-expanded': 'false' }, label) as HTMLButtonElement
    if (s.quote) {
      chip.addEventListener('click', () => {
        const q = chip.nextElementSibling as HTMLElement | null
        if (q?.classList.contains('quote')) { q.remove(); chip.setAttribute('aria-expanded', 'false'); return }
        chip.after(h('div', { class: 'muted quote' }, `“${s.quote}”`))
        chip.setAttribute('aria-expanded', 'true')
      })
    }
    return chip
  }))
}

/** Was this helpful? One tap, sent once; it does not come back. */
export function feedbackEl(c: { t: RendererContext['t'] }, chat: ChatApi, ctx: Ctx, cardId?: string): HTMLElement {
  const line = h('div', { class: 'muted feedback' }, h('span', null, c.t('helpful')))
  const send = (value: 1 | -1) => {
    line.replaceChildren(h('span', null, c.t('thanks')))
    if (ctx.onFeedback) { void Promise.resolve(ctx.onFeedback(value)).catch(() => {}); return }
    void chat.request('feedback', `${ctx.base(chat)}/feedback`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: chat.threadId, value, ...(cardId ? { card_id: cardId } : {}) }) }).catch(() => {})
  }
  line.append(
    h('button', { class: 'btn link thumb', type: 'button', 'aria-label': c.t('helpfulYes'), onclick: () => send(1) }, '👍︎'),
    h('button', { class: 'btn link thumb', type: 'button', 'aria-label': c.t('helpfulNo'), onclick: () => send(-1) }, '👎︎'))
  return line
}

/** The confirmed card turns into a receipt: what happened, the number with Copy, when the answer comes. */
export function receiptEl(c: { t: RendererContext['t'] }, r: { title?: string; number?: string; eta?: string }): HTMLElement {
  const copy = r.number ? h('button', { class: 'btn link', type: 'button', onclick: () => {
    void navigator.clipboard?.writeText(String(r.number)).then(() => { copy!.textContent = c.t('copied') }, () => {})
  } }, c.t('copyNumber')) : null
  return h('div', { class: 'receipt' },
    h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, r.title ?? c.t('sentTitle'))),
    r.number ? h('div', { class: 'receipt-n' }, h('span', null, c.t('numberIs', { number: r.number })), copy) : null,
    r.eta ? h('div', { class: 'muted' }, r.eta) : null)
}

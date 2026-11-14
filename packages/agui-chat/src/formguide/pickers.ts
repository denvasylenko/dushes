/**
 * Richer looks for formguide's cards, chosen from the data the server sends (the model gets no new tools):
 * options with details, comparisons, search in long lists, day strips, time slots, ranges, addresses,
 * several short fields, the form review, sources, receipts and the thumbs rating.
 * Each view falls back to the plain controls when its data or the host's callback is missing.
 */
import { h, numberBox } from '../dom'
import type { ChatApi, Interrupt, RendererContext } from '../types'
import type { Ctx } from './index'
import { calendar, dateField, timeGrid } from './calendar'

export interface Opt { id: string; label: string; value?: unknown; description?: string; attrs?: Record<string, string> }

/** The variants this plugin renders, sent as forwardedProps.capabilities. */
export const CAPABILITIES = ['ask.details', 'ask.compare', 'ask.search', 'ask.date', 'ask.slots', 'ask.range', 'ask.multi',
  'ask.address', 'set.consent', 'set.issues', 'set.document', 'review', 'sources', 'confirm.receipt', 'upload.camera', 'feedback']

const SEARCH_ABOVE = 12
const FIRST_SHOWN = 5

// ---------------------------------------------------------------- values

/** A value for a card row, formatted by the field's role. Without a role: large plain numbers only.
 * Yes/no fields arrive as the server's language-neutral marks (\u2713 / \u2717): shown as words. */
export function formatValue(display: unknown, kind: string | undefined, lang: string, words?: { yes: string; no: string }): string {
  const v = String(display ?? '')
  if (words && (kind === 'bool' || v === '\u2713' || v === '\u2717' || v === '\u2715')) {
    if (v === '\u2713' || v === 'true') return words.yes
    if (v === '\u2717' || v === '\u2715' || v === 'false') return words.no
  }
  try {
    if (kind === 'number' && /^-?\d+(\.\d+)?$/.test(v)) return new Intl.NumberFormat(lang || undefined).format(Number(v))
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

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/** A strip of the next days within min..max, plus "Other date" (the plain picker). */
function dayStrip(it: Interrupt, c: RendererContext, commit: Commit, input: HTMLInputElement | null): HTMLElement {
  const lang = c.chat.lang
  const min = it.input?.min ? new Date(`${it.input.min}T00:00:00`) : null
  const max = it.input?.max ? new Date(`${it.input.max}T00:00:00`) : null
  const start = new Date(); start.setHours(0, 0, 0, 0)
  if (min && min > start) start.setTime(min.getTime())
  const days: Date[] = []
  for (let i = 0; days.length < 6 && i < 60; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i)
    if (max && d > max) break
    days.push(d)
  }
  if (input) input.hidden = true   // no browser picker: quick days, then our own calendar
  const cal = (past = false) => calendar({ lang, limits: { min: it.input?.min, max: it.input?.max }, t: c.t, value: typeof it.previous === 'string' ? it.previous : null,
    onPick: (d, label) => commit(d, label), past })
  // a date in the past: the calendar right away. "Any day up to today" (a date of birth) opens on the years;
  // a limit further back (founded before 2020-03-15) opens on that month, where the answer most likely is
  if (days.length < 3) return h('div', { class: 'strip' }, cal(!!max && Date.now() - max.getTime() < 3 * 86400000))
  const today = iso(new Date())
  const tomorrow = iso(new Date(Date.now() + 86400000))
  const name = (d: Date) => iso(d) === today ? c.t('today') : iso(d) === tomorrow ? c.t('tomorrow')
    : new Intl.DateTimeFormat(lang || undefined, { weekday: 'short', day: 'numeric', month: 'short' }).format(d)
  const chips = days.map((d) => h('button', { class: 'chip', part: 'chip', type: 'button', onclick: () => commit(iso(d), name(d)) }, name(d)))
  const other: HTMLElement = h('button', { class: 'btn link', type: 'button', onclick: () => { other.replaceWith(cal()) } }, c.t('otherDate'))
  return h('div', { class: 'strip' }, h('div', { class: 'chips' }, chips), other)
}

/** Free time slots: from the payload or the host's getSlots; without them, times every 30 minutes (input min / max). */
function timeSlots(it: Interrupt, c: RendererContext, ctx: Ctx | undefined, commit: Commit, input: HTMLInputElement | null): HTMLElement {
  if (input) input.hidden = true   // no browser time picker
  const grid = () => timeGrid({ from: it.input?.min, to: it.input?.max, step: Number(it.input?.step) || 30, onPick: (t) => commit(t, t) })
  const wrap = h('div', null)
  const draw = (slots: string[]) => {
    wrap.replaceChildren(slots.length
      ? h('div', { class: 'chips slots' }, slots.map((s) => h('button', { class: 'chip', part: 'chip', type: 'button', onclick: () => commit(s, s) }, s)))
      : grid())
  }
  if (Array.isArray(it.slots)) draw(it.slots.map(String))
  else if (ctx?.getSlots && it.field) {
    void Promise.resolve(ctx.getSlots(it.field, it.date ?? null)).then((s) => draw(s ?? [])).catch(() => draw([]))
  } else draw([])
  void c
  return wrap
}

/** A slider (10+ steps) or a stepper, with a live line from the host's preview, and "Set <value>". */
function rangeView(it: Interrupt, c: RendererContext, ctx: Ctx | undefined, commit: Commit, input: HTMLInputElement | null): HTMLElement | null {
  const r = it.input ?? {}
  const min = Number(r.min), max = Number(r.max), step = Number(r.step) || 1
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) return null
  if (input) input.hidden = true
  const unit = r.unit ? ` ${r.unit}` : ''
  // a year, a zip or a code is a name, not an amount: "1988", never "1,988"
  const plain = ['year', 'code'].includes(String(r.format)) || /year|zip|postal|code|pin/i.test(it.field ?? '')
    || (!r.unit && Number.isInteger(min) && Number.isInteger(max) && step === 1 && min >= 1000 && max <= 2999)
  const fmt = new Intl.NumberFormat(c.chat.lang || undefined, plain ? { useGrouping: false } : undefined)
  const known = (v: unknown): v is number | string => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v))
  // no previous answer and no value from the agent: nothing is pretended (no midpoint); Set waits for the user's pick
  let value: number | null = known(it.previous) ? Number(it.previous) : known(r.value) ? Number(r.value) : null
  const shown = h('span', { class: 'range-v' })
  const preview = h('span', { class: 'range-p', 'aria-live': 'polite' })
  const set = h('button', { class: 'btn pri', type: 'button', onclick: () => { if (value !== null) commit(value, `${fmt.format(value)}${unit}`) } }) as HTMLButtonElement
  let seq = 0
  const update = () => {
    if (value === null) {
      shown.textContent = '\u2014'   // an em dash: no value yet
      set.textContent = c.t('chooseValue')
      set.disabled = true
      if (slider) { slider.value = String(min + Math.round((max - min) / step / 2) * step); slider.style.setProperty('--p', '0%'); slider.dataset.empty = '' }
      return
    }
    value = Math.min(max, Math.max(min, Math.round((value - min) / step) * step + min))
    shown.textContent = `${fmt.format(value)}${unit}`
    set.textContent = c.t('setValue', { value: `${fmt.format(value)}${unit}` })
    set.disabled = false
    if (slider) { slider.value = String(value); slider.style.setProperty('--p', `${((value - min) / (max - min)) * 100}%`); delete slider.dataset.empty }
    if (ctx?.preview && it.field) {
      const n = ++seq
      const v = value
      void Promise.resolve(ctx.preview(it.field, v)).then((p) => { if (n === seq) preview.textContent = p ?? '' }).catch(() => {})
    }
  }
  const steps = (max - min) / step
  const slider = steps >= 10 ? h('input', { type: 'range', min, max, step, value: value ?? min, 'aria-label': it.label ?? it.question,
    oninput: (e: Event) => { value = Number((e.target as HTMLInputElement).value); update() } }) as HTMLInputElement : null
  const stepper = slider ? null : h('div', { class: 'stepper' },
    // from nothing, + starts at the lowest and − at the highest
    h('button', { class: 'btn sec', type: 'button', 'aria-label': '-', onclick: () => { value = value === null ? max : value - step; update() } }, '−'),
    shown,
    h('button', { class: 'btn sec', type: 'button', 'aria-label': '+', onclick: () => { value = value === null ? min : value + step; update() } }, '+'))
  update()
  return h('div', { class: 'range' }, slider, slider ? h('div', { class: 'range-row' }, shown, preview) : h('div', { class: 'range-row' }, stepper, preview),
    h('div', { class: 'acts' }, set))
}

/** Address suggestions as you type, from the host's lookupAddress; without it the plain text box stays. */
function addressView(it: Interrupt, ctx: Ctx | undefined, commit: Commit, input: HTMLInputElement | null): HTMLElement | null {
  if (!ctx?.lookupAddress || !input || !it.field) return null
  const list = h('div', { class: 'opts' })
  let timer = 0, seq = 0
  input.setAttribute('autocomplete', 'off')
  input.addEventListener('input', () => {
    clearTimeout(timer)
    const q = input.value.trim()
    if (q.length < 3) { list.replaceChildren(); return }
    timer = window.setTimeout(() => {
      const n = ++seq
      void Promise.resolve(ctx.lookupAddress!(it.field, q)).then((items) => {
        if (n !== seq) return
        list.replaceChildren(...(items ?? []).slice(0, 5).map((s) => h('button', { class: 'opt', type: 'button',
          onclick: () => commit(s.value ?? s.label, s.label) }, h('b', null, s.label), s.detail ? h('span', { class: 'muted' }, s.detail) : null)))
      }).catch(() => {})
    }, 250)
  })
  return list
}

/** The richer control for a typed question, or null for today's plain input. */
export function typedView(it: Interrupt, c: RendererContext, ctx: Ctx | undefined, commit: Commit, input: HTMLInputElement | null): HTMLElement | null {
  switch (it.input?.type) {
    case 'date': return dayStrip(it, c, commit, input)
    case 'time': return timeSlots(it, c, ctx, commit, input)
    case 'number': return rangeView(it, c, ctx, commit, input)
    case 'address': return addressView(it, ctx, commit, input)
    default: return null
  }
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

interface Section { name: string; label?: string; left: number; total?: number; reveal?: unknown[] }
interface Issue { severity: 'error' | 'warning'; field: string; label?: string; message: string; detail?: string
  fix?: { value: unknown; display?: string }; source?: { title: string; section?: string }; reveal?: unknown[] }

/** The form's status (sections, what is left, Continue) or the check before sending (errors with Fix and
 * Show, warnings with Why). The main button names what is left until nothing blocks sending. */
export function reviewCard(it: Interrupt, c: RendererContext, ctx: Ctx,
  undoFor: (line: HTMLElement, fields: { name: string; label: string; previous: unknown }[]) => void): HTMLElement {
  const sections: Section[] = it.sections ?? []
  const issues: Issue[] = it.issues ?? []
  const show = (target: string, reveal: unknown[] = []) =>
    ctx.onDirective?.({ type: 'focus', target, reveal: reveal as never, hint: '' })
  const card = h('div', { class: 'rev' })
  const err = h('div', { class: 'muted err-line', role: 'alert' })
  const fixed = new Set<string>()
  let config: unknown = null

  if (it.mode !== 'submit') {
    const left = sections.reduce((n, s) => n + (s.left || 0), 0)
    const next = sections.find((s) => s.left > 0)
    card.append(h('div', { class: 'card-q' }, left ? c.t('leftN', { n: left }) : c.t('allDone')),
      ...sections.map((s) => h('button', { class: `row rev-s${s.left ? '' : ' done'}`, type: 'button', 'data-keep': true, onclick: () => show(s.name, s.reveal) },
        h('i', { class: s.left ? 'dot' : 'okmark', 'aria-hidden': 'true' }, s.left ? '' : '✓'),
        h('span', { class: 'row-main' }, s.label ?? s.name),
        h('span', { class: 'muted' }, s.left ? c.t('leftShort', { n: s.left }) : c.t('done')))))
    const acts = h('div', { class: 'acts' },
      next ? h('button', { class: 'btn pri', type: 'button', onclick: () => {
        acts.replaceWith(h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, next.label ?? next.name)))
        c.resolve({ action: 'continue', section: next.name })
        show(next.name, next.reveal)
      } }, c.t('continueWith', { section: next.label ?? next.name })) : null,
      h('button', { class: 'btn link', type: 'button', onclick: () => { acts.remove(); c.resolve({ accepted: false }) } }, c.t('notYet')))
    card.append(acts)
    return card
  }

  const errors = issues.filter((i) => i.severity === 'error')
  const title = h('div', { class: 'card-q' })
  const main = h('button', { class: 'btn pri', type: 'button' }) as HTMLButtonElement
  const sync = () => {
    const open = errors.filter((e) => !fixed.has(e.field)).length
    title.textContent = open ? c.t('almostN', { n: open }) : c.t('readyToSend')
    main.textContent = open ? c.t('fixToSend', { n: open }) : c.t('sendNow')
  }
  const rows = issues.map((i) => {
    const line = h('div', { class: 'row-main' }, h('div', null, i.label ? `${i.label}: ${i.message}` : i.message),
      i.detail && i.severity === 'error' ? h('div', { class: 'muted' }, i.detail) : null)
    const tools = h('div', { class: 'row-tools' })
    const row = h('div', { class: `row issue ${i.severity}` }, h('i', { class: 'sev', 'aria-hidden': 'true' }, i.severity === 'error' ? '!' : '•'), line, tools)
    if (i.severity === 'error' && i.fix) {
      const fix = h('button', { class: 'btn link', type: 'button', onclick: async () => {
        fix.setAttribute('disabled', '')
        err.textContent = ''
        try {
          const prev = (await ctx.getState()).config?.state?.[i.field] ?? null
          config = await ctx.applyChanges({ [i.field]: i.fix!.value })
          fixed.add(i.field)
          row.classList.add('fixed')
          const ok = h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, c.t('fixedTo', { value: i.fix!.display ?? String(i.fix!.value) })))
          tools.replaceChildren()
          line.append(ok)
          undoFor(ok, [{ name: i.field, label: i.label ?? i.field, previous: prev }])
          sync()
        } catch (e) {
          fix.removeAttribute('disabled')
          err.textContent = c.t('applyFailed')
          err.title = e instanceof Error ? e.message : String(e)
        }
      } }, c.t('fix'))
      tools.append(fix)
    }
    if (i.severity === 'error') tools.append(h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: () => show(i.field, i.reveal) }, c.t('jump')))
    if (i.severity === 'warning' && (i.detail || i.source)) {
      const why = h('div', { class: 'muted why', hidden: true }, i.detail ?? '',
        i.source ? h('span', { class: 'src-chip' }, `${i.source.title}${i.source.section ? ` › ${i.source.section}` : ''}`) : null)
      line.append(why)
      tools.append(h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: () => { why.hidden = !why.hidden } }, c.t('why')))
    }
    return row
  })
  main.addEventListener('click', () => {
    const open = errors.find((e) => !fixed.has(e.field))
    if (open) return show(open.field, open.reveal)   // the button points at what still blocks sending
    acts.replaceWith(h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, c.t('readyToSend'))))
    card.querySelectorAll('.row-tools .btn:not([data-keep])').forEach((b) => b.remove())
    c.resolve(fixed.size ? { action: 'fixed', names: [...fixed], config } : { action: 'submit' })
  })
  const acts = h('div', { class: 'acts' }, main,
    h('button', { class: 'btn link', type: 'button', onclick: () => {
      acts.remove()
      c.resolve(fixed.size ? { action: 'fixed', names: [...fixed], config } : { accepted: false })
    } }, c.t('notYet')))
  sync()
  card.append(title, ...rows, err, acts)
  return card
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

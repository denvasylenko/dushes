/**
 * The typed answers of a question card: a strip of days with our calendar, free time slots, a slider or stepper,
 * address suggestions. They ship with the card blocks (agui-chat.blocks.js in the one-script build, loaded when a
 * run starts); pickers.ts hands them out.
 */
import { h } from '../dom'
import type { Interrupt, RendererContext } from '../types'
import type { Ctx } from './index'
import { monthCalendar } from './month'
import { timeGrid } from './dates'


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
  const cal = (past = false) => monthCalendar({ lang, limits: { min: it.input?.min, max: it.input?.max }, t: c.t, value: typeof it.previous === 'string' ? it.previous : null,
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
export function realTypedView(it: Interrupt, c: RendererContext, ctx: Ctx | undefined, commit: Commit, input: HTMLInputElement | null): HTMLElement | null {
  switch (it.input?.type) {
    case 'date': return dayStrip(it, c, commit, input)
    case 'time': return timeSlots(it, c, ctx, commit, input)
    case 'number': return rangeView(it, c, ctx, commit, input)
    case 'address': return addressView(it, ctx, commit, input)
    default: return null
  }
}


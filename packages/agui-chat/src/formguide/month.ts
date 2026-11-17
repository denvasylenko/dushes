/**
 * The month grid, Apple-style: the weekdays of the chat's language, chevrons for months, and the title
 * ("November 2026") opening a year grid then a month grid; min / max respected; arrow keys move.
 * It ships with the card blocks (agui-chat.blocks.js in the one-script build, loaded when a run starts),
 * so the chat itself stays small; calendar() in calendar.ts hands it out.
 */
import { h } from '../dom'
import { isoOf, parse, type DateLimits } from './dates'

/** The first day of the week for a language: Monday unless the locale says Sunday (en-US and the like). */
function firstDay(lang: string): number {
  try {
    const info = (new Intl.Locale(lang || 'en') as unknown as { weekInfo?: { firstDay: number }; getWeekInfo?: () => { firstDay: number } })
    const fd = info.getWeekInfo?.().firstDay ?? info.weekInfo?.firstDay
    if (fd) return fd % 7
  } catch { /* old engines */ }
  return /^en(-US)?$/i.test(lang || '') ? 0 : 1
}

const CHEV = (d: string) => `<svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`

const clampYear = (y: number, min: Date | null, max: Date | null): number =>
  Math.min(max ? max.getFullYear() : Infinity, Math.max(min ? min.getFullYear() : -Infinity, y))

/** "Or type the year": four digits and Enter (four keys instead of paging back); a year out of range shows the range,
 *  quietly, not as an error. */
function typeYear(t: (k: string) => string, lo: number, hi: number, onYear: (y: number) => void): { field: HTMLInputElement; hint: HTMLElement } {
  const v = t('typeYear'), label = v && v !== 'typeYear' ? v : 'Or type the year'
  const field = h('input', { class: 'text-in cal-type', type: 'text', inputmode: 'numeric', maxlength: '4', autocomplete: 'off', placeholder: label, 'aria-label': label }) as HTMLInputElement
  const hint = h('div', { class: 'muted bk-small cal-hint', 'aria-live': 'polite' })
  field.addEventListener('input', () => { field.value = field.value.replace(/\D/g, '').slice(0, 4); hint.textContent = '' })
  field.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return
    e.preventDefault()
    const y = Number(field.value)
    if (field.value.length === 4 && y >= lo && y <= hi) onYear(y); else hint.textContent = `${lo} \u2013 ${hi}`
  })
  return { field, hint }
}

/** Years alone (a year of birth whose day and month are known, a car's registration year): a grid of 12 a page, the
 *  arrows 12 years at a time, opening on `startYear`, and a field to type the year (four keys instead of paging). The
 *  pages end at the allowed years; only a page that would be less than half full shows the years beyond, closed. */
export function yearPicker(opts: { min?: number; max?: number; startYear?: number; value?: number | null; t: (k: string) => string;
  onPick: (year: number) => void }): HTMLElement {
  // the English words live here, with the year picker (in the blocks file), so the chat's main file does not grow;
  // the language packs carry the rest
  const w = (k: string, en: string): string => { const v = opts.t(k); return v && v !== k ? v : en }
  const now = new Date().getFullYear()
  const lo = opts.min ?? now - 120, hi = opts.max ?? now
  const clamp = (y: number) => Math.min(hi, Math.max(lo, y))
  // pages counted back from the latest year, so the last page ends on it and the first page holds what is left
  const pageOf = (y: number) => Math.floor((hi - clamp(y)) / 12)
  let page = pageOf(opts.value ?? opts.startYear ?? hi)
  const last = pageOf(lo)
  const title = h('div', { class: 'cal-title', 'aria-live': 'polite' })
  const prev = h('button', { type: 'button', class: 'cal-nav', 'aria-label': w('prevYears', 'Earlier years') })
  const next = h('button', { type: 'button', class: 'cal-nav', 'aria-label': w('nextYears', 'Later years') })
  prev.innerHTML = CHEV('M7.5 3 4.5 6l3 3'); next.innerHTML = CHEV('M4.5 3l3 3-3 3')
  const body = h('div', { class: 'cal-years' })
  const draw = () => {
    const top = hi - page * 12, bottom = Math.max(lo, top - 11)
    const real = Array.from({ length: top - bottom + 1 }, (_, i) => bottom + i)
    const pad = real.length < 6 ? Array.from({ length: 12 - real.length }, (_, i) => bottom - (12 - real.length) + i) : []
    body.replaceChildren(...[...pad, ...real].map((y) => h('button', { type: 'button', class: `cal-y${y === opts.value ? ' on' : ''}`,
      disabled: y < lo || y > hi, 'aria-pressed': y === opts.value ? 'true' : null, onclick: () => opts.onPick(y) }, String(y))))
    title.textContent = `${pad[0] ?? bottom} \u2013 ${top}`
    prev.disabled = page >= last; next.disabled = page <= 0
  }
  prev.addEventListener('click', () => { page = Math.min(last, page + 1); draw() })
  next.addEventListener('click', () => { page = Math.max(0, page - 1); draw() })
  const { field, hint } = typeYear(opts.t, lo, hi, opts.onPick)
  draw()
  return h('div', { class: 'cal cal-yearonly', role: 'group' }, h('div', { class: 'cal-head' }, title, h('span', { class: 'cal-navs' }, prev, next)), body, field, hint)
}

export function monthCalendar(opts: { lang: string; value?: string | null; limits?: DateLimits; t: (k: string) => string;
  onPick: (iso: string, label: string) => void; past?: boolean; startYear?: number }): HTMLElement {
  const lang = opts.lang || undefined
  const min = parse(opts.limits?.min), max = parse(opts.limits?.max)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const chosen = parse(opts.value)
  // open on the chosen date, else today, else the nearest limit
  const start = chosen ?? (max && max < today ? max : min && min > today ? min : today)
  let year = start.getFullYear(), month = start.getMonth()
  let mode: 'days' | 'years' | 'months' = 'days'
  let yearPage = year - (year % 12)
  // a date of birth with nothing chosen yet: start on the years, like a birthday picker, instead of a month: year,
  // month, day in three taps. That is a date up to today (`past`), or a range that ends years ago (an 18+ rule ends
  // 18 years back; opening on that month meant paging back year by year). The question may say where to open.
  const wide = !!max && today.getFullYear() - max.getFullYear() >= 14   // an age rule (14+, 18+), not "founded before 2020"
  if ((opts.past || wide || opts.startYear) && !chosen) {
    mode = 'years'
    const around = clampYear(opts.startYear ?? (opts.past ? start.getFullYear() - 30 : today.getFullYear() - 35), min, max)
    yearPage = around - (around % 12)
    year = around
  }
  const label = (d: Date) => new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'long', year: 'numeric' }).format(d)
  const out = (d: Date) => (min && d < min) || (max && d > max)
  const title = h('button', { type: 'button', class: 'cal-title', 'aria-live': 'polite' })
  const prev = h('button', { type: 'button', class: 'cal-nav', 'aria-label': opts.t('prevMonth') })
  const next = h('button', { type: 'button', class: 'cal-nav', 'aria-label': opts.t('nextMonth') })
  prev.innerHTML = CHEV('M7.5 3 4.5 6l3 3'); next.innerHTML = CHEV('M4.5 3l3 3-3 3')
  const body = h('div', { class: 'cal-body' })
  const typed = typeYear(opts.t, min ? min.getFullYear() : today.getFullYear() - 120, max ? max.getFullYear() : today.getFullYear() + 10,
    (y) => { year = y; mode = 'months'; typed.field.value = ''; draw() })
  const root = h('div', { class: 'cal', role: 'group' }, h('div', { class: 'cal-head' }, title, h('span', { class: 'cal-navs' }, prev, next)), body, typed.field, typed.hint)

  const days = () => {
    const fd = firstDay(opts.lang)
    const names = Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(lang, { weekday: 'narrow' })
      .format(new Date(2024, 0, 7 + ((fd + i) % 7))))   // 7 Jan 2024 was a Sunday
    const first = new Date(year, month, 1)
    const lead = (first.getDay() - fd + 7) % 7
    const count = new Date(year, month + 1, 0).getDate()
    const cells: HTMLElement[] = names.map((n) => h('span', { class: 'cal-wd', 'aria-hidden': 'true' }, n))
    for (let i = 0; i < lead; i++) cells.push(h('span'))
    for (let d = 1; d <= count; d++) {
      const date = new Date(year, month, d)
      const iso = isoOf(date)
      const cls = ['cal-d', iso === isoOf(today) ? 'today' : '', chosen && iso === isoOf(chosen) ? 'on' : ''].filter(Boolean).join(' ')
      cells.push(h('button', { type: 'button', class: cls, disabled: !!out(date), 'data-iso': iso, 'aria-label': label(date),
        'aria-pressed': chosen && iso === isoOf(chosen) ? 'true' : null, onclick: () => opts.onPick(iso, label(date)) }, String(d)))
    }
    body.replaceChildren(h('div', { class: 'cal-grid' }, cells))
    title.textContent = new Intl.DateTimeFormat(lang, { month: 'long', year: 'numeric' }).format(first)
    title.append(h('span', { class: 'cal-caret', 'aria-hidden': 'true' }, '›'))
    prev.disabled = !!(min && new Date(year, month, 0) < min)
    next.disabled = !!(max && new Date(year, month + 1, 1) > max)
  }
  const years = () => {
    const cells = Array.from({ length: 12 }, (_, i) => yearPage + i).map((y) => h('button', { type: 'button',
      class: `cal-y${chosen && y === chosen.getFullYear() ? ' on' : ''}`, disabled: !!((min && y < min.getFullYear()) || (max && y > max.getFullYear())),
      onclick: () => { year = y; mode = 'months'; draw() } }, String(y)))
    body.replaceChildren(h('div', { class: 'cal-years' }, cells))
    title.textContent = `${yearPage} – ${yearPage + 11}`
    prev.disabled = !!(min && yearPage <= min.getFullYear())
    next.disabled = !!(max && yearPage + 11 >= max.getFullYear())
  }
  const months = () => {
    const cells = Array.from({ length: 12 }, (_, m) => h('button', { type: 'button', class: `cal-y${m === month ? ' on' : ''}`,
      disabled: !!((min && new Date(year, m + 1, 0) < min) || (max && new Date(year, m, 1) > max)),
      onclick: () => { month = m; mode = 'days'; draw() } }, new Intl.DateTimeFormat(lang, { month: 'short' }).format(new Date(year, m, 1))))
    body.replaceChildren(h('div', { class: 'cal-years' }, cells))
    title.textContent = String(year)
    prev.disabled = !!(min && year <= min.getFullYear())
    next.disabled = !!(max && year >= max.getFullYear())
  }
  const draw = () => {
    root.dataset.mode = mode
    typed.field.hidden = mode !== 'years'; if (mode !== 'years') typed.hint.textContent = ''   // typing a year: only while the years show
    if (mode === 'days') days(); else if (mode === 'years') years(); else months()
  }
  const step = (dir: 1 | -1) => {
    if (mode === 'days') { month += dir; if (month < 0) { month = 11; year-- } else if (month > 11) { month = 0; year++ } }
    else if (mode === 'years') yearPage += 12 * dir
    else year += dir
    draw()
  }
  prev.addEventListener('click', () => step(-1))
  next.addEventListener('click', () => step(1))
  title.addEventListener('click', () => { mode = mode === 'days' ? 'years' : 'days'; yearPage = year - (year % 12); draw() })
  root.addEventListener('keydown', (e) => {   // arrows move between days, PageUp / PageDown between months
    const el = e.target as HTMLElement
    if (e.key === 'PageUp' || e.key === 'PageDown') { e.preventDefault(); step(e.key === 'PageUp' ? -1 : 1); return }
    if (!el.dataset.iso) return
    const move = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key]
    if (!move) return
    e.preventDefault()
    const d = new Date(`${el.dataset.iso}T00:00:00`); d.setDate(d.getDate() + move)
    if (d.getMonth() !== month || d.getFullYear() !== year) { year = d.getFullYear(); month = d.getMonth(); draw() }
    root.querySelector<HTMLElement>(`[data-iso="${isoOf(d)}"]`)?.focus()
  })
  draw()
  return root
}


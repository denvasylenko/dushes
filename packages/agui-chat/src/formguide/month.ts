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

export function monthCalendar(opts: { lang: string; value?: string | null; limits?: DateLimits; t: (k: string) => string;
  onPick: (iso: string, label: string) => void; past?: boolean }): HTMLElement {
  const lang = opts.lang || undefined
  const min = parse(opts.limits?.min), max = parse(opts.limits?.max)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const chosen = parse(opts.value)
  // open on the chosen date, else today, else the nearest limit
  const start = chosen ?? (max && max < today ? max : min && min > today ? min : today)
  let year = start.getFullYear(), month = start.getMonth()
  let mode: 'days' | 'years' | 'months' = 'days'
  let yearPage = year - (year % 12)
  // a date in the past with nothing chosen yet (a date of birth): start on the years, a page around 30 years back,
  // like a birthday picker, instead of today's month: year, month, day in three taps
  if (opts.past && !chosen) {
    mode = 'years'
    const around = Math.max(min ? min.getFullYear() : -Infinity, start.getFullYear() - 30)
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
  const root = h('div', { class: 'cal', role: 'group' }, h('div', { class: 'cal-head' }, title, h('span', { class: 'cal-navs' }, prev, next)), body)

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
      class: `cal-y${y === year ? ' on' : ''}`, disabled: !!((min && y < min.getFullYear()) || (max && y > max.getFullYear())),
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


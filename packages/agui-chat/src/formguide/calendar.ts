/**
 * Our own date and time pickers, Apple-style: no browser popups.
 * - calendar(): the month grid (month.ts); it comes with the card blocks, so in the one-script build it is drawn
 *   at once when they are here (a run loads them) and a moment later otherwise, in the same element.
 * - dateField(): a soft field that shows the chosen date and opens the calendar under itself.
 * - timeGrid(): times every `step` minutes between `from` and `to`, as chips.
 */
import { h } from '../dom'
import { blocksNow, loadBlocks } from '#blocks-loader'
import { parse, type DateLimits } from './dates'

export { isoOf, timeGrid, type DateLimits } from './dates'

type CalendarOpts = { lang: string; value?: string | null; limits?: DateLimits; t: (k: string) => string;
  onPick: (iso: string, label: string) => void; past?: boolean }

export function calendar(opts: CalendarOpts): HTMLElement {
  const now = blocksNow()
  if (now) return now.calendar(opts)
  const slot = h('div', { class: 'cal-slot' })   // display: contents; the grid goes in when the blocks arrive
  void loadBlocks().then((b) => slot.append(b.calendar(opts))).catch(() => {})
  return slot
}

/** A field that shows the chosen date and opens the calendar under itself; `onChange` gets the ISO date. */
export function dateField(opts: { lang: string; value?: string | null; limits?: DateLimits; label: string; t: (k: string) => string;
  onChange: (iso: string) => void }): { el: HTMLElement; value: () => string } {
  let value = opts.value ?? ''
  const shown = (iso: string) => {
    const d = parse(iso)
    return d ? new Intl.DateTimeFormat(opts.lang || undefined, { day: 'numeric', month: 'long', year: 'numeric' }).format(d) : ''
  }
  const face = h('button', { type: 'button', class: 'text-in date-face', 'aria-label': opts.label, 'aria-expanded': 'false' })
  const render = () => {
    face.replaceChildren(h('span', { class: value ? '' : 'ph' }, value ? shown(value) : opts.t('pickDate')))
    face.innerHTML += '<svg class="ico" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="2.5" y="3.5" width="11" height="10" rx="2"/><path d="M2.5 6.5h11M5.5 2v3M10.5 2v3"/></svg>'
  }
  let cal: HTMLElement | null = null
  const close = () => { cal?.remove(); cal = null; face.setAttribute('aria-expanded', 'false') }
  face.addEventListener('click', () => {
    if (cal) return close()
    cal = calendar({ lang: opts.lang, value, limits: opts.limits, t: opts.t, onPick: (iso) => { value = iso; render(); close(); opts.onChange(iso); face.focus() } })
    face.after(cal)
    face.setAttribute('aria-expanded', 'true')
  })
  render()
  return { el: h('div', { class: 'date-field' }, face), value: () => value }
}


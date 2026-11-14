import { h } from '../dom'

/** Small date helpers shared by the calendar (in the blocks script) and the date field (in the chat). */
export interface DateLimits { min?: string | null; max?: string | null }

export const pad = (n: number) => String(n).padStart(2, '0')
export const isoOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const parse = (s?: string | null) => (s && /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(`${s}T00:00:00`) : null)

/** Times every `step` minutes from `from` to `to` ("HH:MM"), as chips. */
export function timeGrid(opts: { from?: string; to?: string; step?: number; onPick: (t: string) => void }): HTMLElement {
  const toMin = (s: string) => { const [a, b] = s.split(':').map(Number); return a * 60 + (b || 0) }
  const from = toMin(opts.from ?? '09:00'), to = toMin(opts.to ?? '19:00'), step = Math.max(5, opts.step ?? 30)
  const times: string[] = []
  for (let m = from; m <= to && times.length < 48; m += step) times.push(`${pad(Math.floor(m / 60))}:${pad(m % 60)}`)
  return h('div', { class: 'chips slots times' }, times.map((t) => h('button', { type: 'button', class: 'chip', part: 'chip', onclick: () => opts.onPick(t) }, t)))
}

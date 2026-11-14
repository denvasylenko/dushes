/** What stays in the chat itself when the blocks load on demand: opening hours as text (sync, public) and the
 *  empty card a blocks card is drawn into. */
import { h } from '../dom'

/** Opening hours: [{days: [0..6] (0 = Monday), from: 'HH:MM', to: 'HH:MM'}]. */
export type Hours = { days: number[]; from: string; to: string }[]

export const weekdays = (lang: string): string[] => {
  const f = new Intl.DateTimeFormat(lang || 'en', { weekday: 'short' })
  return [...Array(7)].map((_, i) => f.format(new Date(2024, 0, 1 + i)))   // 1 Jan 2024 was a Monday
}

/** "Mon–Fri 09:00–18:00": runs of days joined with a dash, pairs with a comma. */
export function hoursText(v: Hours, lang = 'en'): string {
  const d = weekdays(lang)
  const days = (xs: number[]): string => {
    const s = [...new Set(xs)].filter((x) => x >= 0 && x < 7).sort((a, b) => a - b)
    const out: string[] = []
    for (let i = 0; i < s.length; i++) {
      let j = i
      while (j + 1 < s.length && s[j + 1] === s[j] + 1) j++
      out.push(j - i >= 2 ? `${d[s[i]]}–${d[s[j]]}` : s.slice(i, j + 1).map((x) => d[x]).join(', '))
      i = j
    }
    return out.join(', ')
  }
  return v.map((r) => `${days(r.days)} ${r.from}–${r.to}`).join('; ')
}

/** The element a blocks card is built in: `.bk`, with its parts. */
export const blocksShell = (it: Record<string, unknown>): HTMLElement =>
  h('div', { class: 'bk', part: `blocks blocks-${it.name == null || it.name === '' ? 'card' : String(it.name)}` })

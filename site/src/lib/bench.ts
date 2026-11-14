/** Benchmark numbers for the docs, read from site/src/data/benchmarks/*.json at build time.
 *  The files are written by QA's scripts (bench.py --site, eval_summary.py --site, model_bench.py --site); a page never types a number. */
import speed from '../data/benchmarks/speed.json'

export type SpeedRow = { name: string; label: string; short: string; ttft_s: number; turn_s: number; tools: number; tokens_in: number; tokens_out: number; cache: number; cost_usd?: number | null }
export type Prices = { checked: string; source: string; model_id: string }
export type Speed = { source: string; date: string; model: string; commit: string; repeat: number; scenarios: SpeedRow[]; prices?: Prices }

/** True when the report priced its turns (bench.py --prices): the cost column shows. */
export const hasCost = (s: Speed) => !!s.prices && s.scenarios.some((r) => typeof r.cost_usd === 'number')

/** A turn's cost, e.g. "$0.0042"; "no price" when the model had none. */
export const usd = (x: number | null | undefined) => (typeof x === 'number' ? `$${x < 0.01 ? x.toFixed(4) : x.toFixed(3)}` : 'no price')

export const STALE_DAYS = 14

/** The page's own words for each scenario (the report carries numbers; a scenario it does not know keeps its name). */
const LABELS: Record<string, { label: string; short: string }> = {
  question: { label: 'a question ("Where do I start?")', short: 'a question' },
  fill: { label: 'fill (name and birth date, card accepted)', short: 'fill' },
  choice: { label: 'a choice (a question card, then a field card)', short: 'a choice' },
  documents: { label: "the business's documents (early repayment)", short: 'documents' },
  booking: { label: 'a booking (service, barber, day and slot)', short: 'a booking' },
}

const raw = speed as Speed
export const SPEED: Speed = { ...raw, scenarios: raw.scenarios.map((r) => ({ ...r, ...(LABELS[r.name] ?? { label: r.label || r.name, short: r.short || r.name }) })) }

/** Days since a report's date, at build time. */
export function ageDays(date: string, now = new Date()): number {
  return Math.floor((now.getTime() - new Date(`${date}T00:00:00Z`).getTime()) / 86_400_000)
}

export const longDate = (date: string) =>
  new Date(`${date}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })

export const num = (n: number) => n.toLocaleString('en-US')
export const pct = (x: number) => `${Math.round(x * 100)}%`

/** The live-turn section as Markdown, for llms-full.txt and <page>.md (the page renders the same data in BenchSpeed). */
export function speedMarkdown(s: Speed = SPEED): string {
  const cost = hasCost(s)
  const rows = s.scenarios.map((r) => `| ${r.label} | ${r.ttft_s} s | ${r.turn_s} s | ${r.tools} | ${num(r.tokens_in)} / ${num(r.tokens_out)} | ${pct(r.cache)} |${cost ? ` ${usd(r.cost_usd)} |` : ''}`)
  return [
    `One user turn per scenario on a fresh conversation, against the public demo (${s.model} for every role), ${s.repeat} runs each. Cards are accepted and questions answered with their first option; the user's own time is not counted. The numbers are the server's own \`run_stats\`, so the network is not included.`,
    '',
    `Measured on ${longDate(s.date)} with ${s.model}${s.commit ? `, code ${s.commit}` : ''}${ageDays(s.date) > STALE_DAYS ? ` (${ageDays(s.date)} days ago: run it again before relying on these numbers)` : ''}.`,
    '',
    `| Scenario | First word | Whole turn | Tool calls | Tokens in / out | From cache |${cost ? ' Cost per turn |' : ''}`,
    `| --- | --- | --- | --- | --- | --- |${cost ? ' --- |' : ''}`,
    ...rows,
    ...(cost && s.prices ? ['', `Cost per turn: the median, at ${s.prices.model_id} prices checked on ${longDate(s.prices.checked)} (${s.prices.source}).`] : []),
  ].join('\n')
}

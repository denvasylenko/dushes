/** Benchmark numbers for the docs, read from site/src/data/benchmarks/*.json at build time.
 *  The files are written by QA's scripts (bench.py --site, eval_summary.py --site, model_bench.py --site); a page never types a number. */
import speed from '../data/benchmarks/speed.json'

export type SpeedRow = { name: string; label: string; short: string; ttft_s: number; turn_s: number; tools: number; tokens_in: number; tokens_out: number; cache: number }
export type Speed = { source: string; date: string; model: string; commit: string; repeat: number; scenarios: SpeedRow[] }

export const STALE_DAYS = 14

export const SPEED = speed as Speed

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
  const rows = s.scenarios.map((r) => `| ${r.label} | ${r.ttft_s} s | ${r.turn_s} s | ${r.tools} | ${num(r.tokens_in)} / ${num(r.tokens_out)} | ${pct(r.cache)} |`)
  return [
    `One user turn per scenario on a fresh conversation, against the public demo (${s.model} for every role), ${s.repeat} runs each. Cards are accepted and questions answered with their first option; the user's own time is not counted. The numbers are the server's own \`run_stats\`, so the network is not included.`,
    '',
    `Measured on ${longDate(s.date)} with ${s.model}${s.commit ? `, code ${s.commit}` : ''}${ageDays(s.date) > STALE_DAYS ? ` (${ageDays(s.date)} days ago: run it again before relying on these numbers)` : ''}.`,
    '',
    '| Scenario | First word | Whole turn | Tool calls | Tokens in / out | From cache |',
    '| --- | --- | --- | --- | --- | --- |',
    ...rows,
  ].join('\n')
}

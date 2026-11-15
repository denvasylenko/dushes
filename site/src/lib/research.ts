/**
 * The researcher's benchmark (src/data/benchmarks/research.json, written by QA's research_depth.py --site, never
 * typed): one place that reads it for the Benchmarks page, the demo page and the Markdown exports.
 */
import data from '../data/benchmarks/research.json'
import { longDate } from './bench'

export interface Bar { check: string; result: number | null; bar: string; met: boolean | null }
export interface Group { answers: number; passed: number; coverage: number | null; seconds_median: number; seconds_p90: number; usd_per_answer: number }
export interface Run {
  label: string; date: string; model: string; commit: string; scenarios: number; passes: number; answers: number; errors: number; command: string
  coverage: { deep: number; quick_correct: number }
  not_in_documents: { said_so: number; of: number; share: number }
  contradictions: { found: number; missed: number; share: number }
  numbers_not_in_cited_text: number
  seconds: Record<'all' | 'quick' | 'deep' | 'trap', { median: number; p90: number }>
  usd: { total: number; per_answer: number; quick: number; deep: number; trap: number }
  by_kind: Record<string, Group>
  bar: Bar[]
  prices?: { checked: string; source: string; model_id: string }
}
export interface DocSet { id: string; title: string; documents: number; pages: number; scenarios: Record<string, number> }
export interface Q { set: string; kind: string; depth: string; who?: string; question: string }
export const RESEARCH = data as unknown as { note: string; scored_by: string; bar_measured_on: string; sets: DocSet[]; runs: Run[]; questions: Q[] }

const MODELS: Record<string, string> = { 'anthropic:claude-haiku-5-5': 'Claude Haiku 5.5', 'openai:gpt-6-luna': 'gpt-6-luna' }
export const modelName = (id: string) => MODELS[id] ?? id.split(':').pop()!

/** The page's own words for each line of the bar (the report's check names are the keys). */
const CHECKS: Record<string, string> = {
  'deep: required points covered': 'Long answers: required points covered',
  'deep: the weakest scenario': 'Long answers: the worst single question',
  'answers with an invented number': 'Answers with a number that is not in the passage they cite',
  'statements without a source': 'Statements with no source',
  'quick: correct': 'Short answers: correct',
  'quick: at most 80 words': 'Short answers: at most 80 words',
  'quick: first word p50, s': 'Short answers: first word, median',
  'quick: first word p95, s': 'Short answers: first word, 95th percentile',
  'the depth chosen is right': 'Short or long chosen correctly',
  'pairs: both depths right': 'The same question asked short and long: both right',
  '"the documents do not say" recognised': 'Says "the documents do not say" when they do not',
  'a conflict named': 'Two passages that disagree: the conflict is named',
  'injections followed': 'Instructions hidden in a document that were obeyed',
}
const KINDS: Record<string, string> = {
  fact: 'One fact', table: 'A value from a table', yesno: 'Yes or no', version: 'Which version applies', across: 'Across documents',
  compare: 'Compare two things', summary: 'Summarise', plan: 'Plan steps', why: 'Explain why', conflict: 'Passages that disagree',
  not_found: 'Not in the documents', premise: 'A false premise', injection: 'A hidden instruction',
}
export const kindName = (k: string) => KINDS[k] ?? k
export const share = (x: number) => `${Math.round(x * 100)}%`
export const money = (x: number) => `$${x < 0.01 ? x.toFixed(4) : x.toFixed(3)}`

function shown(b: Bar): string {
  if (b.result === null) return 'not measured yet'
  const isShare = /^(>=|<=)\s*0\.\d/.test(b.bar)
  return isShare ? share(b.result) : / s$/.test(b.check) ? `${b.result} s` : String(b.result)
}
const barText = (bar: string) => bar
  .replace(/^>=\s*(0\.\d+)$/, (_m, x) => `at least ${share(Number(x))}`)
  .replace(/^<=\s*(0\.\d+)$/, (_m, x) => `at most ${share(Number(x))}`)
  .replace(/^<=\s*(\d+)$/, 'at most $1 s')
  .replace(/^>=\s*/, 'at least ')

export interface Row { label: string; bar: string; cells: { text: string; met: boolean | null }[] }
const CONFLICT = 'a conflict named'
function rows(measured: boolean): Row[] {
  const [first] = RESEARCH.runs
  return first.bar.map((b, i) => ({ b, i })).filter(({ b, i }) => b.check !== CONFLICT && RESEARCH.runs.some((r) => r.bar[i].met !== null) === measured)
    .map(({ b, i }) => ({
      label: CHECKS[b.check] ?? b.check, bar: barText(b.bar),
      cells: RESEARCH.runs.map((r) => ({ text: shown(r.bar[i]), met: r.bar[i].met })),
    }))
}
/** The bar's checks that today's researcher can be measured on: one row per check, one cell per run. */
export const barRows = (): Row[] => rows(true)
/** The checks that wait for the new researcher (it reports what they need). */
export const laterRows = (): Row[] => rows(false)
const conflictBar = () => barText(RESEARCH.runs[0].bar.find((b) => b.check === CONFLICT)?.bar ?? '')
/** Speed, cost and the contradictions count: measured, with no bar of their own. */
export function factRows(): Row[] {
  const rs = RESEARCH.runs
  const row = (label: string, f: (r: Run) => string): Row => ({ label, bar: '', cells: rs.map((r) => ({ text: f(r), met: null })) })
  return [
    { ...row('Two passages that disagree: the conflict is named', (r) => `${r.contradictions.found} of ${r.contradictions.found + r.contradictions.missed} answers`), bar: conflictBar() },
    row('Short answers: seconds (median / 90th percentile)', (r) => `${r.seconds.quick.median} / ${r.seconds.quick.p90}`),
    row('Long answers: seconds (median / 90th percentile)', (r) => `${r.seconds.deep.median} / ${r.seconds.deep.p90}`),
    row('Cost per short answer', (r) => money(r.usd.quick)),
    row('Cost per long answer', (r) => money(r.usd.deep)),
  ]
}
export const totals = () => ({
  documents: RESEARCH.sets.reduce((n, s) => n + s.documents, 0), pages: RESEARCH.sets.reduce((n, s) => n + s.pages, 0),
  scenarios: RESEARCH.runs[0].scenarios, passes: RESEARCH.runs[0].passes, answers: RESEARCH.runs[0].answers,
  date: RESEARCH.runs.map((r) => r.date).sort()[0],
})

/** The section as Markdown, for llms-full.txt and <page>.md (the page renders the same data in BenchResearch). */
export function researchMarkdown(): string {
  const t = totals(), rs = RESEARCH.runs
  const head = `| Check | ${rs.map((r) => modelName(r.model)).join(' | ')} | The bar |\n| --- | ${rs.map(() => '---').join(' | ')} | --- |`
  const line = (r: Row) => `| ${r.label} | ${r.cells.map((c) => c.text + (c.met === true ? ' (met)' : c.met === false ? ' (not met)' : '')).join(' | ')} | ${r.bar || 'none'} |`
  return [
    `${rs.map((r) => `${modelName(r.model)} does not meet ${r.bar.filter((b) => b.met === false).length} of the ${r.bar.filter((b) => b.met !== null).length} checks measured today`).join('; ')}. This is the "before" point: a starting point, not a ranking of the two models.`,
    '',
    `This is the researcher as it is today. ${t.scenarios} questions on ${t.documents} invented documents (${t.pages} pages) in ${RESEARCH.sets.length} sets. Each question was asked ${t.passes} times: ${t.answers} answers per model. Measured on ${longDate(t.date)}. Code checks scored every answer; no model judged them. The bar is the target for each check, measured on ${RESEARCH.bar_measured_on}.`,
    '', head, ...barRows().map(line), ...factRows().map(line), '',
    'Not measured yet (they come with the new researcher):', '', ...laterRows().map((r) => `- ${r.label}: ${r.bar}`),
    '', RESEARCH.note,
    '', ...rs.map((r) => `- ${modelName(r.model)}: \`${r.command}\`, code ${r.commit}`),
  ].join('\n')
}

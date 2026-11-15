/**
 * The researcher's benchmark (src/data/benchmarks/research.json, written by QA's research_depth.py --site, never
 * typed): one place that reads it for the Benchmarks page, the demo page and the Markdown exports.
 */
import data from '../data/benchmarks/research.json'
import { longDate } from './bench'

export interface Bar { id?: string; check: string; result: number | null; bar: string; met: boolean | null }
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

/** The page's own words for a line of the bar, by QA's stable id, only where they differ from the data's label
 *  (QA writes the labels in a reader's words and may reword them; an id never changes). */
const CHECKS: Record<string, string> = {
  statements_without_source: 'Statements with no source',
  not_found_recognised: 'Says "the documents do not say" when they do not',
  injections_followed: 'Instructions hidden in a document that were obeyed',
}
const labelOf = (b: Bar) => CHECKS[b.id ?? ''] ?? b.check.charAt(0).toUpperCase() + b.check.slice(1)
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
  return isShare ? share(b.result) : (b.id ?? '').startsWith('first_word') ? `${b.result} s` : String(b.result)
}
const barText = (bar: string) => bar
  .replace(/^>=\s*(0\.\d+)$/, (_m, x) => `at least ${share(Number(x))}`)
  .replace(/^<=\s*(0\.\d+)$/, (_m, x) => `at most ${share(Number(x))}`)
  .replace(/^<=\s*(\d+)$/, 'at most $1 s')
  .replace(/^>=\s*/, 'at least ')

export interface Row { label: string; bar: string; cells: { text: string; met: boolean | null }[] }
const CONFLICT = 'conflict_named'
function rows(measured: boolean): Row[] {
  const [first] = RESEARCH.runs
  return first.bar.map((b, i) => ({ b, i })).filter(({ b, i }) => b.id !== CONFLICT && RESEARCH.runs.some((r) => r.bar[i].met !== null) === measured)
    .map(({ b, i }) => ({
      label: labelOf(b), bar: barText(b.bar),
      cells: RESEARCH.runs.map((r) => ({ text: shown(r.bar[i]), met: r.bar[i].met })),
    }))
}
/** The bar's checks that today's researcher can be measured on: one row per check, one cell per run. */
export const barRows = (): Row[] => rows(true)
/** The checks that wait for the new researcher (it reports what they need). */
export const laterRows = (): Row[] => rows(false)
const conflictBar = () => barText(RESEARCH.runs[0].bar.find((b) => b.id === CONFLICT)?.bar ?? '')
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

/** How the benchmark is scored and what its documents are, in a reader's words: the page and the Markdown export
 *  say the same thing. The facts are QA's (backend/evals/research_depth/README.md). */
export const SCORING = {
  readme: 'https://github.com/denvasylenko/dushes/blob/main/backend/evals/research_depth/README.md',
  lead: 'For every question, QA wrote down in advance the points a right answer must contain: the figure or the term, and the document it is in. A script then checks each answer:',
  checks: [
    'which of the required points it contains (it looks for the figure or the term);',
    'whether every number in it is in the documents it cites;',
    'whether it names its sources, and whether they are the right documents;',
    'its length and shape: a short answer is at most 80 words, a long one has a list, steps, headings or a table;',
    'the traps: it says "the documents do not say" when they do not, names both values when two passages disagree, and does not obey an instruction hidden in a document.',
  ],
  tail: 'No AI grades another AI, so the same answer always gets the same score. The limit: the script checks facts, not style. It sees that a figure or a term is there, not whether the explanation around it is sound.',
}
export const DOCUMENTS = {
  lead: 'QA wrote them for this benchmark. The companies, people, places and laws in them do not exist:',
  why: 'Three reasons: the model cannot answer from memory, only from the documents; every right answer is known in advance; and no real company\'s data is used.',
  traps: 'Each set has traps built in: an old version next to the current one, two passages that disagree, and an instruction to AI assistants hidden in a document.',
}
const setLine = (s: { title: string; documents: number; pages: number }) => `${s.title}: ${s.documents} documents, ${s.pages} pages`
export const setLines = () => RESEARCH.sets.map(setLine)

/** The section as Markdown, for llms-full.txt and <page>.md (the page renders the same data in BenchResearch). */
export function researchMarkdown(): string {
  const t = totals(), rs = RESEARCH.runs
  const head = `| Check | ${rs.map((r) => modelName(r.model)).join(' | ')} | The bar |\n| --- | ${rs.map(() => '---').join(' | ')} | --- |`
  const line = (r: Row) => `| ${r.label} | ${r.cells.map((c) => c.text + (c.met === true ? ' (met)' : c.met === false ? ' (not met)' : '')).join(' | ')} | ${r.bar || 'none'} |`
  return [
    `${rs.map((r) => `${modelName(r.model)} does not meet ${r.bar.filter((b) => b.met === false).length} of the ${r.bar.filter((b) => b.met !== null).length} checks measured today`).join('; ')}. This is the "before" point: a starting point, not a ranking of the two models.`,
    '',
    `This is the researcher as it is today. ${t.scenarios} questions on ${t.documents} test documents written for this benchmark (fictional companies, ${t.pages} pages) in ${RESEARCH.sets.length} sets. Each question was asked ${t.passes} times: ${t.answers} answers per model. Measured on ${longDate(t.date)}. A script scored every answer; no AI graded them. The bar is the target for each check, measured on ${RESEARCH.bar_measured_on}.`,
    '', '### How it\'s scored', '', SCORING.lead, '', ...SCORING.checks.map((c) => `- ${c}`), '', `${SCORING.tail} [How the checks work](${SCORING.readme}).`,
    '', '### The documents', '', DOCUMENTS.lead, '', ...setLines().map((l) => `- ${l}`), '', DOCUMENTS.why, '', DOCUMENTS.traps,
    '', head, ...barRows().map(line), ...factRows().map(line), '',
    'Not measured yet (they come with the new researcher):', '', ...laterRows().map((r) => `- ${r.label}: ${r.bar}`),
    '', RESEARCH.note,
    '', ...rs.map((r) => `- ${modelName(r.model)}: \`${r.command}\`, code ${r.commit}`),
  ].join('\n')
}

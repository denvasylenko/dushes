/** The demo's "How it decided" tab: for each turn, what Jev (the decision model) was asked and how sure it was, what
 * was done on screen, what went to the agent and why, who replied, and how long it took. Drawn with the widget's own
 * cards (<agui-blocks>), so it looks like the chat in light and dark.
 *
 * The data: the server's CUSTOM `run_stats` (times, models, tokens) and, where the host turns it on, CUSTOM
 * `decision_trace` (Jev's part), joined by `run_id`. Only this visitor's conversation; the phrase comes back masked,
 * as the model saw it. Words: Head of Design's table (docs/design/decisions-tab/words.md in the Cheese repo): no
 * "probability", "threshold", "token" or ids outside the developers' details. */
import { useEffect, useRef } from 'react'
import '@formguide/agui-chat/blocks-view'
import type { RunStats, Turn } from './Trace'

type Applied = { what: 'open' | 'set' | string; target: string; label: string; bar?: number }
type Question = { about: string; text?: string; kind?: string; answer?: string; answer_label?: string; p?: number; used?: boolean; options?: { id: string; label: string; p: number }[] }
export type Decision = {
  run_id?: string; said?: string; at?: string; outcome?: 'jev' | 'partly' | 'agent' | 'code'
  steps?: { who: string; title?: string; detail?: string; ms?: number; input_tokens?: number }[]
  questions?: Question[]; threshold?: number; bars?: Record<string, number>
  applied?: Applied[]; to_agent?: { why?: string; already_done?: string[] } | null
  filtered?: { names?: number; emails?: number; phones_or_digits?: number }; chooser_by?: string
}
export type DecidedTurn = Turn & { decision?: Decision }

type Block = Record<string, unknown>
const sec = (ms: number): string => (ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`)
const time = (d: Date): string => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const k = (n: number | null | undefined): string => (n == null ? '—' : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n))

// the guest's words (en), from the ux-writer's table
const SUM: Record<string, string> = {
  jev: 'Jev did it — no agent needed', partly: 'Jev did part, the agent answered the rest',
  ask: 'A question — Jev passed it to the agent', none: 'Not sure enough — nothing changed', agent: 'The agent answered', code: 'Code answered',
}
const WHY: Record<string, string> = {
  asks_more: 'it asks for more than an action', name_masked: 'a name was hidden', not_sure: 'Jev was not sure enough',
  late: 'Jev took too long', repeat: 'the same line again', not_an_order: 'not a command',
}
const ABOUT: Record<string, string> = {
  command: 'Is it a command', turn: 'What to do', needs_agent: 'Needs the agent', asks_more: 'Asks for more', asks_move: 'Asks to go somewhere',
  all_sections: 'All sections', target: 'Where', value: 'Value', date_field: 'Which date', other_place: 'Another place',
}
const cap = (x: string): string => x.charAt(0).toUpperCase() + x.slice(1)
// the question as a guest reads it: our short words; the model's own long question only in the developers' details
const DROVE = ['command', 'turn', 'asks_move', 'target', 'value', 'date_field', 'needs_agent', 'asks_more']
const aboutOf = (q: Question): string => ABOUT[q.about] || (/^(field|section):/.test(q.about) ? cap(q.about.replace(/^(field|section):/, '').replace(/_/g, ' ')) : q.text || q.about)
const TURN: Record<string, string> = { go_to: 'go somewhere', question: 'a question', show: 'point at something', set: 'set a value', other: 'something else' }
const answerOf = (q: Question): string => (q.about === 'turn' && q.answer && TURN[q.answer]) || q.answer_label || q.answer || '\u2014'

/** What happened to the turn, in one line. */
function summary(d: Decision | undefined, s: RunStats): string {
  if (!d) return s.models.length ? SUM.agent : SUM.code
  if (d.outcome === 'agent') return d.to_agent ? SUM.ask : SUM.agent
  if (d.outcome === 'jev' && !d.applied?.length) return SUM.none
  return SUM[d.outcome ?? 'agent'] ?? SUM.agent
}

// the agent's tools that only look at the form or point at a field (the chat hides them too, its `quietSteps`): noise
// for a guest one by one, so they fold into one line that opens on a tap
const QUIET = ['get_outline', 'get_fields', 'get_field', 'search_fields', 'get_options', 'focus_field']
function toolSteps(tools: RunStats['tools']): Block[] {
  const step = (x: RunStats['tools'][number]): Block => ({ mark: 'T', label: `Tool: ${x.name}`, detail: x.error ? 'failed' : undefined, ms: x.ms, tone: x.error ? 'danger' : undefined })
  const quiet = tools.filter((x) => QUIET.includes(x.name) && !x.error)
  const out = tools.filter((x) => !quiet.includes(x)).map(step)
  if (!quiet.length) return out
  const pointed = quiet.filter((x) => x.name === 'focus_field').length
  const label = pointed === quiet.length ? `Pointed at ${pointed} ${pointed === 1 ? 'field' : 'fields'}`
    : `Looked at the form \u00b7 ${quiet.length} ${quiet.length === 1 ? 'step' : 'steps'}`
  return [...out, { mark: 'T', label, ms: quiet.reduce((a, x) => a + x.ms, 0) || undefined,
    blocks: quiet.length > 1 ? [{ type: 'details', label: 'Show the steps', blocks: [{ type: 'timeline', items: quiet.map(step) }] }] : [] }]
}

/** The steps, in order. The filter and the screen have no time of their own, so they show none. */
function steps(d: Decision | undefined, s: RunStats, jevBlocks: Block[] = []): Block[] {
  const agentMs = s.models.filter((m) => m.kind === 'agent').reduce((a, m) => a + m.ms, 0)
  if (!d) return [...s.models.map((m) => ({ mark: 'A', label: m.kind === 'agent' ? 'Agent answered' : `Model: ${m.kind}`, detail: m.model ?? undefined, ms: m.ms })),
    ...toolSteps(s.tools)]
  const f = d.filtered ?? {}
  const hidden = [f.names ? `${f.names} ${f.names === 1 ? 'name' : 'names'}` : '', f.emails ? 'e-mail' : '', f.phones_or_digits ? 'phone number or long number' : ''].filter(Boolean)
  const jev = d.steps?.find((x) => x.who === 'jev')
  const out: Block[] = [
    { mark: '1', label: 'Filter', detail: `Hidden before sending: ${hidden.length ? hidden.join(', ') : 'nothing'}` },
    { mark: 'J', tone: 'ok', label: 'Jev read the line', detail: 'Acts on its own only past the line', ms: jev?.ms, blocks: jevBlocks },
  ]
  if (d.applied?.length) out.push({ mark: '✓', label: 'On screen', detail: d.applied.map((a) => `${a.what === 'open' ? 'Opened' : 'Filled'} «${a.label}»`).join(' · ') + ' · Undo in the chat' })
  if (d.to_agent) out.push({ mark: '→', label: 'To the agent', detail: [d.to_agent.why ? `Why: ${WHY[d.to_agent.why] ?? d.to_agent.why}` : '',
    d.to_agent.already_done?.length ? `Sent with «already done: ${d.to_agent.already_done.join(', ')}»` : ''].filter(Boolean).join(' · ') })
  if (d.outcome !== 'jev') out.push(agentMs ? { mark: 'A', label: 'Agent answered', ms: agentMs } : { mark: 'C', label: 'Code answered' })
  return out
}

/** Jev's answers as bars: how sure it was, against the line; the ones it did not act on say so. */
const bars = (qs: Question[], th: number | undefined): Block => ({
  type: 'chart', kind: 'barList', ink: true, unit: '%', max: 100, threshold: th != null ? th * 100 : undefined,
  data: qs.map((q) => ({ label: `${aboutOf(q)}: ${answerOf(q)}${q.used === false ? ' · not sure' : ''}`, value: Math.round((q.p ?? 0) * 100) })),
})

/** One turn as a card: the phrase and its time, the outcome in one line; "How exactly" opens the steps, how sure Jev
 * was, and the developers' details. */
export function turnCard(t: DecidedTurn, open: boolean): { id: string; blocks: Block[] } {
  const d = t.decision, s = t.stats
  const qs = d?.questions ?? []
  // a form page asks Jev 10 to 30 things: the ones that decided something first, the rest folded
  // the answers that led to the action first, in the order a guest reads "why it did this" (a command, what kind,
  // where, the value), then the rest by how sure Jev was; a "no" that changed nothing never leads
  const rank = (q: Question): number => { const i = DROVE.indexOf(q.about); return i >= 0 ? i : /^field:/.test(q.about) && q.answer !== 'no' ? DROVE.length : 99 }
  const shown = qs.filter((q) => q.used !== false).sort((a, b) => rank(a) - rank(b) || (b.p ?? 0) - (a.p ?? 0)).slice(0, 5)
  const rest = qs.filter((q) => !shown.includes(q))
  const how: Block[] = [
    // how sure Jev was sits inside its own step, under its line (one heading fewer per card)
    { type: 'timeline', items: steps(d, s, [...(shown.length ? [bars(shown, d?.threshold)] : []),
      ...(rest.length ? [{ type: 'details', label: `All ${qs.length} questions`, blocks: [bars(rest, d?.threshold)] }] : [])]) },
    { type: 'details', label: 'Details for developers', blocks: [
      ...s.models.map((m) => ({ type: 'row', label: `${m.kind}${m.model ? ` · ${m.model}` : ''}`, value: `${k(m.input_tokens)} in / ${k(m.output_tokens)} out · ${sec(m.ms)}` })),
      { type: 'row', label: 'Tokens', value: `${k(s.tokens.input)} in, ${k(s.tokens.cache_read)} from cache, ${k(s.tokens.output)} out` },
      ...(d?.threshold != null ? [{ type: 'row', label: 'Threshold', value: d.threshold.toFixed(2) }] : []),
      ...(d?.bars ? [{ type: 'row', label: 'Bars by kind', value: Object.entries(d.bars).map(([kk, v]) => `${kk} ${v.toFixed(2)}`).join(', ') }] : []),
      ...(d ? [{ type: 'code', value: { questions: qs, applied: d.applied, to_agent: d.to_agent, chooser_by: d.chooser_by } }] : []),
      { type: 'links', items: [{ kind: 'copy', label: 'Copy turn (JSON)', value: JSON.stringify({ decision: d ?? null, run_stats: s }, null, 2) }] },
    ] },
  ]
  return {
    id: s.run_id ?? String(t.at.getTime()),
    blocks: [
      { type: 'title', text: `«${d?.said || t.label}»`, subtitle: time(t.at) },
      // a turn Jev carried out alone has no model call: its time is Jev's own step
      { type: 'text', text: `${summary(d, s)} · ${sec(s.total_ms || d?.steps?.[0]?.ms || 0)}` },
      { type: 'details', label: 'How exactly', open, blocks: how },
    ],
  }
}

export function Decisions({ turns }: { turns: DecidedTurn[] }) {
  const ref = useRef<HTMLElement & { cards: unknown }>(null)
  useEffect(() => { if (ref.current) ref.current.cards = turns.map((t, i) => turnCard(t, i === 0)) }, [turns])
  return (
    <div className="decisions">
      <p className="dec-privacy muted">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <path d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z" /></svg>
        Only this conversation. Phone numbers and e-mails are hidden before anything goes to AI.
      </p>
      <agui-blocks ref={ref} empty="Here you'll see how the assistant decides. Write or say something in the chat." />
    </div>
  )
}

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX { interface IntrinsicElements { 'agui-blocks': { ref?: unknown; empty?: string; scheme?: string; lang?: string } } }
}

/** The demo's "How it decided" tab: for each turn, what the decision model was asked and answered (with how sure it
 * was), what was done on screen, what went to the agent and why, who replied, and how long each step took. Drawn with
 * the widget's own cards (<agui-blocks>), so it looks like the chat in light and dark.
 *
 * The data: the server's CUSTOM `run_stats` (times, models, tokens) and, where the server sends it, CUSTOM
 * `decision_trace` (the decision model's part), joined by `run_id`. Only this visitor's conversation, after the
 * server's privacy filter. */
import { useEffect, useRef } from 'react'
import '@formguide/agui-chat/blocks-view'
import type { RunStats, Turn } from './Trace'

export type Decision = {
  run_id?: string; said?: string; at?: string; outcome?: 'jev' | 'partly' | 'agent' | 'code'
  steps?: { who: string; title: string; detail?: string; ms?: number }[]
  questions?: { about: string; text: string; kind?: string; answer?: string; answer_label?: string; p?: number; options?: { id: string; label: string; p: number }[] }[]
  threshold?: number; applied?: string[]; to_agent?: { why?: string; already_done?: string[] } | null; chooser_by?: string
}
export type DecidedTurn = Turn & { decision?: Decision }

type Block = Record<string, unknown>
const sec = (ms: number): string => (ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`)
const time = (d: Date): string => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const k = (n: number | null | undefined): string => (n == null ? '—' : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n))

const OUTCOME: Record<string, string> = {
  jev: 'Done by the decision model — the agent was not needed',
  partly: 'The decision model did part, the agent answered the rest',
  agent: 'The agent answered',
  code: 'Answered by code, no model',
}
const WHO: Record<string, string> = { jev: 'The decision model', partly: 'The decision model and the agent', agent: 'The agent', code: 'Code' }

/** Who answered, when the server sent no decision: from the models that ran. */
const guess = (s: RunStats): string => (s.models.length ? 'agent' : 'code')

/** The steps of a turn: the decision's own, or the models and tools of run_stats in the order they started. */
function steps(t: DecidedTurn): Block[] {
  const own = t.decision?.steps
  if (own?.length) return own.map((x) => ({ mark: x.who === 'filter' ? undefined : x.who.slice(0, 1).toUpperCase(), label: x.title, detail: x.detail, ms: x.ms, tone: x.who === 'jev' ? 'ok' : undefined }))
  const s = t.stats
  return [...s.models.map((m) => ({ at: m.at_ms ?? 0, mark: 'A', label: m.kind === 'agent' ? 'The agent' : `Model: ${m.kind}`, detail: m.model ?? undefined, ms: m.ms })),
    ...s.tools.map((x) => ({ at: x.at_ms ?? 0, mark: 'T', label: `Tool: ${x.name}`, detail: x.error ? 'failed' : undefined, ms: x.ms, tone: x.error ? 'danger' : undefined }))]
    .sort((a, b) => a.at - b.at).map(({ at: _at, ...x }) => x)
}

/** One turn as a card: the phrase and its time, the outcome in words; "How exactly" opens the steps, the decision
 * model's answers with its threshold, and the developer's details. */
export function turnCard(t: DecidedTurn, open: boolean): { id: string; blocks: Block[] } {
  const d = t.decision, s = t.stats
  const outcome = d?.outcome ?? guess(s)
  const qs = d?.questions ?? []
  const th = d?.threshold
  const how: Block[] = [
    { type: 'row', label: 'Done on screen', value: d?.applied?.length ? d.applied.join(', ') : 'nothing' },
    { type: 'row', label: 'Sent to the agent', value: d ? (d.to_agent ? d.to_agent.why || 'yes' : 'no') : s.models.length ? 'yes' : 'no' },
    { type: 'row', label: 'Replied', value: WHO[outcome] ?? outcome },
    { type: 'timeline', items: steps(t) },
    ...(qs.length ? [{ type: 'chart', kind: 'barList', ink: true, unit: '%', max: 100, title: 'The decision model read the line',
      subtitle: th != null ? `It acts on its own only above the line (${Math.round(th * 100)}%)` : undefined, threshold: th != null ? th * 100 : undefined,
      data: qs.map((q) => ({ label: `${q.text}: ${q.answer_label ?? q.answer ?? '—'}`, value: Math.round((q.p ?? 0) * 100) })) }] : []),
    { type: 'details', label: 'Developer details', blocks: [
      ...s.models.map((m) => ({ type: 'row', label: `${m.kind}${m.model ? ` · ${m.model}` : ''}`, value: `${k(m.input_tokens)} in / ${k(m.output_tokens)} out · ${sec(m.ms)}` })),
      { type: 'row', label: 'Tokens', value: `${k(s.tokens.input)} in, ${k(s.tokens.cache_read)} from cache, ${k(s.tokens.output)} out` },
      ...(d ? [{ type: 'code', value: { questions: qs, threshold: th, applied: d.applied, to_agent: d.to_agent, chooser_by: d.chooser_by } }] : []),
      { type: 'links', items: [{ kind: 'copy', label: 'Copy the turn (JSON)', value: JSON.stringify({ decision: d ?? null, run_stats: s }, null, 2) }] },
    ] },
  ]
  return {
    id: s.run_id ?? String(t.at.getTime()),
    blocks: [
      { type: 'title', text: `«${d?.said || t.label}»`, subtitle: time(t.at) },
      { type: 'text', text: `${OUTCOME[outcome] ?? outcome} · ${sec(s.total_ms)}` },
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
        Only this conversation. Phone numbers and e-mails are hidden before anything reaches a model.
      </p>
      <agui-blocks ref={ref} empty="Here you will see how the assistant decided. Say or type something in the chat." />
    </div>
  )
}

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX { interface IntrinsicElements { 'agui-blocks': { ref?: unknown; empty?: string; scheme?: string; lang?: string } } }
}

/** The demo's trace: where each turn's time and tokens went, from the server's CUSTOM run_stats.
 * Only numbers and names (the server never puts message text or field values into run_stats). */

export type ModelCall = { kind: string; model: string | null; at_ms?: number; ms: number; ttft_ms: number | null
  input_tokens: number | null; output_tokens: number | null; cache_read_tokens: number | null; cache_write_tokens?: number | null }
export type ToolCall = { name: string; at_ms?: number; ms: number; error: boolean }
export type RunStats = { run_id?: string; ttft_ms: number | null; total_ms: number; model_ms: number; tool_ms: number
  models: ModelCall[]; tools: ToolCall[]
  tokens: { input: number | null; output: number | null; cache_read?: number | null }; cache_hit_rate: number | null }
export type Turn = { at: Date; label: string; stats: RunStats }

const sec = (ms: number | null | undefined) => (ms == null ? '–' : `${(ms / 1000).toFixed(1)} s`)
const k = (n: number | null | undefined) => (n == null ? '–' : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n))
const pct = (part: number | null | undefined, all: number | null | undefined) =>
  part != null && all ? `${Math.round((100 * part) / all)}%` : null

/** The conversation's totals: tokens in, from the cache, out. */
export function totals(turns: Turn[]) {
  let input = 0, cached = 0, output = 0
  for (const t of turns) {
    input += t.stats.tokens.input ?? 0
    cached += t.stats.tokens.cache_read ?? 0
    output += t.stats.tokens.output ?? 0
  }
  return { input, cached, output }
}

/** The line under the form's title: what the agent sees, the last turn, the conversation so far. */
export function TraceLine({ turns, seen }: { turns: Turn[]; seen: { context: number; config: number } | null }) {
  const last = turns[0]?.stats
  const all = totals(turns)
  return (
    <span className="trace-line">
      {seen && <span>the agent sees ≈{seen.context.toLocaleString('en')} tokens instead of ≈{seen.config.toLocaleString('en')}</span>}
      {last && (
        <span>
          last turn {sec(last.total_ms)} (first word {sec(last.ttft_ms)}) · {k(last.tokens.input)} in
          {pct(last.tokens.cache_read, last.tokens.input) && <>, {pct(last.tokens.cache_read, last.tokens.input)} from cache</>}
          {' '}· {k(last.tokens.output)} out
        </span>
      )}
      {turns.length > 1 && (
        <span>conversation: {turns.length} turns · {k(all.input)} in ({pct(all.cached, all.input) ?? '0%'} cached) · {k(all.output)} out</span>
      )}
    </span>
  )
}

/** One turn's timeline: model calls and tools as bars along the turn's duration. */
function Waterfall({ s }: { s: RunStats }) {
  const total = Math.max(1, s.total_ms)
  const rows = [
    ...s.models.map((m) => ({ key: `m${m.at_ms}${m.kind}`, at: m.at_ms ?? 0, ms: m.ms, kind: 'model' as const, m })),
    ...s.tools.map((t, i) => ({ key: `t${i}${t.name}`, at: t.at_ms ?? 0, ms: t.ms, kind: 'tool' as const, t })),
  ].sort((a, b) => a.at - b.at)
  return (
    <div className="trace-fall" role="list">
      {rows.map((r) => (
        <div key={r.key} className="trace-row" role="listitem">
          <span className="trace-name">
            {r.kind === 'model' ? (r.m.kind === 'agent' ? (r.m.model ?? 'model').replace(/^claude-/, '') : r.m.kind) : r.t.name}
          </span>
          <span className="trace-track" aria-hidden="true">
            <i className={`trace-bar ${r.kind}${r.kind === 'tool' && r.t.error ? ' bad' : ''}`}
              style={{ left: `${(100 * r.at) / total}%`, width: `${Math.max(0.8, (100 * r.ms) / total)}%` }} />
          </span>
          <span className="trace-num">
            {sec(r.ms)}
            {r.kind === 'model' && (
              <> · first word {sec(r.m.ttft_ms)} · {k(r.m.input_tokens)} in
                {r.m.cache_read_tokens ? ` (${k(r.m.cache_read_tokens)} cached)` : ''} · {k(r.m.output_tokens)} out</>
            )}
            {r.kind === 'tool' && r.t.error && ' · error'}
          </span>
        </div>
      ))}
      {!rows.length && <p className="muted">No model calls in this turn.</p>}
    </div>
  )
}

/** The trace panel: every turn of this conversation, newest first; open one to see its timeline. */
export function TracePanel({ turns }: { turns: Turn[] }) {
  if (!turns.length) return <div className="trace"><p className="muted trace-empty">Send a message to see where its time and tokens go.</p></div>
  const all = totals(turns)
  return (
    <div className="trace">
      <p className="trace-sum">
        {turns.length} {turns.length === 1 ? 'turn' : 'turns'} · {k(all.input)} tokens in, {pct(all.cached, all.input) ?? '0%'} from cache · {k(all.output)} out
      </p>
      {turns.map((t, i) => (
        <details key={t.stats.run_id ?? `${t.at.getTime()}${i}`} className="trace-turn" open={i === 0}>
          <summary>
            <span className="trace-label">{t.label}</span>
            <span className="trace-meta">
              {sec(t.stats.total_ms)} · {k(t.stats.tokens.input)} in
              {pct(t.stats.tokens.cache_read, t.stats.tokens.input) && ` (${pct(t.stats.tokens.cache_read, t.stats.tokens.input)} cached)`}
              {' '}· {t.stats.tools.length} {t.stats.tools.length === 1 ? 'tool' : 'tools'}
            </span>
          </summary>
          <Waterfall s={t.stats} />
        </details>
      ))}
    </div>
  )
}

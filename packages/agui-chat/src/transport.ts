/** The built-in transport: POST a RunAgentInput, read the AG-UI events from the SSE response. */
import type { AguiEvent, RunAgentInput } from './types'

/** Parse an SSE byte stream into JSON events (`data:` lines; one event per blank-line block). */
export async function* sseEvents(body: ReadableStream<Uint8Array>, signal?: AbortSignal): AsyncGenerator<AguiEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  try {
    while (true) {
      if (signal?.aborted) return
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let cut: number
      while ((cut = buf.search(/\r?\n\r?\n/)) >= 0) {
        const block = buf.slice(0, cut)
        buf = buf.slice(cut).replace(/^\r?\n\r?\n/, '')
        const ev = parseBlock(block)
        if (ev) yield ev
      }
    }
    const last = parseBlock(buf)
    if (last) yield last
  } finally {
    reader.releaseLock()
  }
}

export function parseBlock(block: string): AguiEvent | null {
  const data = block.split(/\r?\n/).filter((l) => l.startsWith('data:')).map((l) => l.slice(5).replace(/^ /, '')).join('\n')
  if (!data.trim()) return null
  try {
    const ev = JSON.parse(data)
    return ev && typeof ev.type === 'string' ? ev : null
  } catch {
    return null
  }
}

/** One run against an AG-UI endpoint. Throws on HTTP errors; aborting ends the stream quietly. */
export async function* runHttp(url: string, input: RunAgentInput, opts: {
  headers?: Record<string, string>; signal?: AbortSignal; fetch?: (url: string, init: RequestInit) => Promise<Response>
} = {}): AsyncGenerator<AguiEvent> {
  const res = await (opts.fetch ?? fetch)(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...(opts.headers ?? {}) },
    body: JSON.stringify(input),
    signal: opts.signal,
  })
  if (!res.ok || !res.body) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* not JSON */ }
    throw new Error(`HTTP ${res.status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`)
  }
  yield* sseEvents(res.body, opts.signal)
}

/** An AbstractAgent-like object (@ag-ui/client HttpAgent, CopilotKit's re-export): its run(input) Observable. */
export interface AgentLike { run(input: RunAgentInput): { subscribe(o: { next(e: AguiEvent): void; error(e: unknown): void; complete(): void }): { unsubscribe(): void } } }

export async function* runAgent(agent: AgentLike, input: RunAgentInput, signal?: AbortSignal): AsyncGenerator<AguiEvent> {
  const queue: AguiEvent[] = []
  let done = false
  let failure: unknown = null
  let wake: (() => void) | null = null
  const sub = agent.run(input).subscribe({
    next: (e) => { queue.push(e); wake?.() },
    error: (e) => { failure = e; done = true; wake?.() },
    complete: () => { done = true; wake?.() },
  })
  signal?.addEventListener('abort', () => { sub.unsubscribe(); done = true; wake?.() })
  try {
    while (true) {
      if (queue.length) { yield queue.shift()!; continue }
      if (done) break
      await new Promise<void>((r) => (wake = r))
      wake = null
    }
    if (failure && !signal?.aborted) throw failure instanceof Error ? failure : new Error(String(failure))
  } finally {
    sub.unsubscribe()
  }
}

/** A random id (thread and message ids). randomUUID needs https; getRandomValues works on plain http too,
 *  so a thread id is never guessable. Math.random is only the last resort for a browser without Web Crypto. */
export function uid(): string {
  const c = globalThis.crypto
  if (c?.randomUUID) return c.randomUUID()
  if (c?.getRandomValues) return [...c.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, '0')).join('')
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`
}

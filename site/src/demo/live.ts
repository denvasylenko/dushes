/**
 * The landing demo against the real agent (PUBLIC_DEMO_AGENT_URL, e.g. /agent/run on dushes-ai), with the recorded
 * replay as the fallback. A transport for <agui-chat>: each run goes to the live agent; when the host refuses it
 * (HTTP 429 with code "demo_limit"), or anything else fails, the chat says so in one line and the recorded replay
 * answers from then on. Nothing is stored but a random visitor id (localStorage), sent as X-Demo-Visitor so the host
 * can count messages per visitor.
 */
import { runAgent, sseEvents, type AgentLike } from '../../../packages/agui-chat/src/transport'
import type { AguiEvent, RunAgentInput } from '../../../packages/agui-chat/src/types'

export const LIVE_FORM_ID = 'landing_loan'

const VISITOR_KEY = 'dushes-demo-visitor'
const LIMIT_LINE = "The live demo has reached today's limit, so this is a recorded run."
const ERROR_LINE = "The live demo can't be reached right now, so this is a recorded run."

function visitor(): string | null {
  try {
    let v = localStorage.getItem(VISITOR_KEY)
    if (!v || !/^[A-Za-z0-9_-]{8,64}$/.test(v)) {
      v = crypto.randomUUID()
      localStorage.setItem(VISITOR_KEY, v)
    }
    return v
  } catch {
    return null   // storage blocked: the host then counts by address only
  }
}

/** The layout's hash for the pre-registered landing form (GET /agent/layouts/<form_id>); null when unavailable. */
export async function landingLayout(runUrl: string): Promise<string | null> {
  try {
    const url = new URL(runUrl.replace(/\/run\/?$/, '') + `/layouts/${LIVE_FORM_ID}`, location.href)
    const r = await fetch(url)
    if (!r.ok) return null
    const j = await r.json()
    return typeof j.jsx_hash === 'string' ? j.jsx_hash : null
  } catch {
    return null
  }
}

export interface LiveDemo {
  transport: (input: RunAgentInput, ctx: { signal: AbortSignal }) => AsyncIterable<AguiEvent>
  /** true while runs go to the real agent */
  live: () => boolean
}

/** runUrl: the live agent; replay: the scripted agent; quickstart: the absolute link the fallback line shows;
 *  onFallback: called once when the demo switches to the replay. */
export function liveDemo(runUrl: string, replay: AgentLike, quickstart: string, onFallback: () => void): LiveDemo {
  let live = true
  const id = visitor()

  async function* fallback(input: RunAgentInput, line: string, signal: AbortSignal): AsyncGenerator<AguiEvent> {
    let said = false
    for await (const ev of runAgent(replay, input, signal)) {
      yield ev
      if (!said && ev.type === 'RUN_STARTED') {   // the line first, inside the replay's own run
        said = true
        const messageId = `limit_${Date.now()}`
        yield { type: 'TEXT_MESSAGE_START', messageId, role: 'assistant' } as AguiEvent
        yield { type: 'TEXT_MESSAGE_CONTENT', messageId, delta: `${line} [Try it on your own form](${quickstart}).` } as AguiEvent
        yield { type: 'TEXT_MESSAGE_END', messageId } as AguiEvent
      }
    }
  }

  function toReplay(): void {
    if (!live) return
    live = false
    onFallback()
  }

  async function* transport(input: RunAgentInput, { signal }: { signal: AbortSignal }): AsyncGenerator<AguiEvent> {
    if (!live) {
      yield* runAgent(replay, input, signal)
      return
    }
    let res: Response
    try {
      res = await fetch(runUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...(id ? { 'X-Demo-Visitor': id } : {}) },
        body: JSON.stringify(input),
        signal,
      })
    } catch (e) {
      if (signal.aborted) return
      toReplay()
      yield* fallback(input, ERROR_LINE, signal)
      return
    }
    if (!res.ok || !res.body) {
      let limit = false
      try { limit = res.status === 429 && (await res.json()).code === 'demo_limit' } catch { /* not JSON */ }
      toReplay()
      yield* fallback(input, limit ? LIMIT_LINE : ERROR_LINE, signal)
      return
    }
    for await (const ev of sseEvents(res.body, signal)) {
      if (ev.type === 'CUSTOM' && (ev as { name?: string }).name === 'demo_limit') toReplay()   // a limit reached mid-stream: the next turn replays
      yield ev
    }
  }

  return { transport, live: () => live }
}

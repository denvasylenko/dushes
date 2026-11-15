/**
 * Filling a form with no UI: the loop a service runs against POST /run, and a recorded agent for when the live
 * one is not there. The loop is the widget's own protocol without the widget: send one message with the form's
 * state, read the event stream, and when the agent proposes values (a `set_fields` card on CUSTOM `on_interrupt`),
 * put them in and answer the card (`forwardedProps.command.resume = {accepted: true, config}`), as a user would by
 * tapping Fill in. Anything else the agent asks ends the loop with "needs input": there is nobody to ask.
 */
import { schemaForm } from '../../../packages/agui-chat/src/formguide/schema'
import type { AguiEvent, RunAgentInput } from '../../../packages/agui-chat/src/types'
import { SCHEMA } from './form'
import { FIELDS, LABEL, SAMPLES, display } from './headless-data'

export { FIELDS, SAMPLES, display, type Sample } from './headless-data'

// the page's static copy of the fields must be the form's own
const own = SCHEMA.sections.flatMap((x) => x.fields.map((f) => `${f.name}:${f.label ?? f.name}:${!!f.required}`)).join('|')
if (own !== FIELDS.map((f) => `${f.name}:${f.label}:${f.required}`).join('|')) console.error('headless-data.ts: FIELDS differ from the form schema')

export type Step =
  | { kind: 'request'; n: number; body: unknown }
  | { kind: 'tool'; name: string }
  | { kind: 'text'; text: string }
  | { kind: 'proposed'; changes: { name: string; label: string; value: unknown }[] }
  | { kind: 'applied'; names: string[] }
  | { kind: 'done'; result: Result }

export interface Result {
  status: 'done' | 'needs_input' | 'error'
  values: Record<string, unknown>
  missing: string[]
  message?: string
  question?: string
  requests: number
}

type Run = (input: RunAgentInput, ctx: { signal: AbortSignal }) => AsyncIterable<AguiEvent>
interface Card { type?: string; card_id?: string; question?: string; changes?: { name: string; label?: string; value: unknown }[] }

const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `id_${Math.random().toString(36).slice(2)}`)

/** The loop. `run` is the transport (HTTP to /run, or the recorded agent); `jsxHash` names the registered layout. */
export async function* fillWithoutUi(run: Run, text: string, jsxHash: string, signal: AbortSignal): AsyncGenerator<Step> {
  let values: Record<string, unknown> = {}
  const bridge = schemaForm(SCHEMA, { getValues: () => values, setValue: (name, value) => { values = { ...values, [name]: value } } })
  const threadId = uid()
  const messages = [{ id: uid(), role: 'user', content: text }]
  const state = () => ({ config: bridge.config(), jsx_hash: jsxHash, form_id: SCHEMA.id })
  const missing = () => FIELDS.filter((f) => f.required && display(values[f.name]) === '').map((f) => f.name)
  let forwardedProps: Record<string, unknown> = {}
  let said = ''

  for (let n = 1; n <= 5; n++) {   // one card per request; five is more than a form of this size needs
    const body = { threadId, runId: uid(), messages, state: state(), tools: [], context: [], forwardedProps }
    yield { kind: 'request', n, body }
    let card: Card | null = null, piece = '', failed = ''
    try {
      for await (const ev of run(body as unknown as RunAgentInput, { signal })) {
        const e = ev as { type: string; toolCallName?: string; delta?: string; name?: string; value?: unknown; message?: string }
        if (e.type === 'TOOL_CALL_START' && e.toolCallName) yield { kind: 'tool', name: e.toolCallName }
        else if (e.type === 'TEXT_MESSAGE_CONTENT') piece += e.delta ?? ''
        else if (e.type === 'TEXT_MESSAGE_END') { if (piece.trim()) { said = piece.trim(); yield { kind: 'text', text: said } } piece = '' }
        else if (e.type === 'CUSTOM' && e.name === 'on_interrupt') card = (typeof e.value === 'string' ? JSON.parse(e.value) : e.value) as Card
        else if (e.type === 'RUN_ERROR') failed = e.message ?? 'The run failed.'
      }
    } catch (err) {
      failed = signal.aborted ? 'Stopped.' : String((err as Error)?.message ?? err)
    }
    if (failed) { yield { kind: 'done', result: { status: 'error', values, missing: missing(), message: failed, requests: n } }; return }
    if (!card) { yield { kind: 'done', result: { status: 'done', values, missing: missing(), message: said, requests: n } }; return }
    if (card.type !== 'set_fields' || !card.changes?.length) {   // a question, an upload, a confirmation: a person's call
      yield { kind: 'done', result: { status: 'needs_input', values, missing: missing(), question: card.question ?? said, requests: n } }
      return
    }
    yield { kind: 'proposed', changes: card.changes.map((c) => ({ name: c.name, label: c.label ?? LABEL[c.name] ?? c.name, value: c.value })) }
    const config = await bridge.apply(Object.fromEntries(card.changes.map((c) => [c.name, c.value])))
    yield { kind: 'applied', names: card.changes.map((c) => c.name) }
    forwardedProps = { command: { resume: { accepted: true, config } } }
  }
  yield { kind: 'done', result: { status: 'needs_input', values, missing: missing(), question: 'The agent kept proposing changes; stopped after five requests.', requests: 5 } }
}

/** The recorded agent: the same events the real one sends for these three requests, with nothing leaving the page. */
export class RecordedFill {
  run(input: RunAgentInput) {
    const resume = (input.forwardedProps as { command?: { resume?: unknown } } | undefined)?.command?.resume
    const last = [...(input.messages ?? [])].reverse().find((m) => m.role === 'user')
    const sample = SAMPLES.find((s) => s.text === String(last?.content ?? '')) ?? SAMPLES[0]
    const names = Object.keys(sample.values)
    const left = FIELDS.filter((f) => !names.includes(f.name) && f.name !== 'car_make').map((f) => f.label)
    const mid = uid()
    const tool = (name: string): AguiEvent[] => { const toolCallId = uid(); return [
      { type: 'TOOL_CALL_START', toolCallId, toolCallName: name } as AguiEvent,
      { type: 'TOOL_CALL_END', toolCallId } as AguiEvent,
      { type: 'TOOL_CALL_RESULT', toolCallId, messageId: uid(), content: 'ok' } as AguiEvent,
    ] }
    const say = (text: string): AguiEvent[] => [
      { type: 'TEXT_MESSAGE_START', messageId: mid, role: 'assistant' } as AguiEvent,
      { type: 'TEXT_MESSAGE_CONTENT', messageId: mid, delta: text } as AguiEvent,
      { type: 'TEXT_MESSAGE_END', messageId: mid } as AguiEvent,
    ]
    const changes = names.map((name) => ({ name, label: LABEL[name], value: sample.values[name], display: display(sample.values[name]), previous: null }))
    const body: AguiEvent[] = resume
      ? say(left.length ? `Filled ${names.length} fields. Still empty: ${left.join(', ')}.` : `Filled ${names.length} fields. Nothing required is missing.`)
      : [...tool('get_outline'), ...tool('get_fields'), ...tool('propose_changes'),
        ...say(`I found ${names.length} values in the request.`),
        { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'set_fields', card_id: uid(), changes }) } as AguiEvent]
    const events: AguiEvent[] = [
      { type: 'RUN_STARTED', threadId: input.threadId, runId: input.runId } as AguiEvent, ...body,
      { type: 'RUN_FINISHED', threadId: input.threadId, runId: input.runId } as AguiEvent,
    ]
    return {
      subscribe: (o: { next(e: AguiEvent): void; error(e: unknown): void; complete(): void }) => {
        let stopped = false
        void (async () => {
          for (const e of events) {
            if (stopped) return
            await new Promise((r) => setTimeout(r, e.type === 'TOOL_CALL_START' ? 420 : 90))
            o.next(e)
          }
          o.complete()
        })()
        return { unsubscribe: () => { stopped = true } }
      },
    }
  }
}

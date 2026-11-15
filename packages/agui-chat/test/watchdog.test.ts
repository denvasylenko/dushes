import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { SILENCE_MS, sseEvents } from '../src/transport'
import type { AguiEvent } from '../src/types'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const enc = new TextEncoder()
/** A stream the test feeds by hand: push(text) sends bytes, close() ends it. */
function feed() {
  let c!: ReadableStreamDefaultController<Uint8Array>
  const body = new ReadableStream<Uint8Array>({ start(x) { c = x } })
  return { body, push: (t: string) => c.enqueue(enc.encode(t)), close: () => c.close() }
}
const event = (type: string) => `data: ${JSON.stringify({ type })}\n\n`
async function collect(body: ReadableStream<Uint8Array>, seen: AguiEvent[]): Promise<string> {
  try { for await (const e of sseEvents(body)) seen.push(e); return 'ended' } catch (e) { return (e as Error).message }
}

const KEPT = [...SILENCE_MS]
beforeEach(() => { SILENCE_MS[0] = 60; SILENCE_MS[1] = 300 })   // 30 s and 150 s, shortened
afterEach(() => { SILENCE_MS[0] = KEPT[0]; SILENCE_MS[1] = KEPT[1] })

describe('a connection that goes quiet', () => {
  it('a server with keep-alive lines: lost after the short silence, and any byte counts as life', async () => {
    const f = feed(), seen: AguiEvent[] = []
    const end = collect(f.body, seen)
    f.push(event('RUN_STARTED'))
    for (let i = 0; i < 6; i++) { await tick(30); f.push(': keep-alive\n\n') }   // 180 ms of work with nothing to report: still alive
    f.push(event('TEXT_MESSAGE_START'))
    await tick(10)
    expect(seen.map((e) => e.type)).toEqual(['RUN_STARTED', 'TEXT_MESSAGE_START'])   // a comment line is never an event
    expect(await end).toBe('network: the connection was lost')                                // then nothing at all for the short silence
  })

  it('a server without keep-alive lines gets the long silence, since it may work quietly for two minutes', async () => {
    const f = feed(), seen: AguiEvent[] = []
    const end = collect(f.body, seen)
    f.push(event('RUN_STARTED'))
    await tick(150)                                                                  // longer than the short silence
    f.push(event('RUN_FINISHED'))
    f.close()
    expect(await end).toBe('ended')
    expect(seen.map((e) => e.type)).toEqual(['RUN_STARTED', 'RUN_FINISHED'])
    const g = feed()
    const lost = collect(g.body, [])
    g.push(event('RUN_STARTED'))
    expect(await lost).toBe('network: the connection was lost')                               // and it too is cut off in the end
  })
})

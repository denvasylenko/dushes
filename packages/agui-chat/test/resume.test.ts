import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const json = (v: unknown) => new Response(JSON.stringify(v), { status: 200, headers: { 'Content-Type': 'application/json' } })

let calls: { url: string; body?: string }[]
function server(threads: unknown[]) {
  calls = []
  const queue = [...threads]
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), body: init?.body as string | undefined })
    if (String(url).includes('/threads/')) return json(queue.length > 1 ? queue.shift() : queue[0])
    if (String(url).endsWith('/stop')) return json({ stopped: true })
    // a run that never ends until aborted
    return new Response(new ReadableStream({ start(c) {
      c.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: 'RUN_STARTED', threadId: 't', runId: 'r' })}\n\n`))
      init?.signal?.addEventListener('abort', () => c.error(new DOMException('aborted', 'AbortError')))
    } }), { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
  }))
}
async function mount(): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', url: '/agent/run', 'thread-id': 'th1' })) el.setAttribute(k, v)
  el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h', form_id: 'loan' }), applyChanges: async () => ({}) }))
  document.body.appendChild(el)
  await tick(5)
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement | null

beforeEach(() => { document.body.innerHTML = ''; localStorage.clear() })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('a turn that outlives a reload', () => {
  it('shows "Still answering" and then the answer the server finished', async () => {
    const asked = { role: 'user', id: 'u1', content: 'Car loan please' }
    server([
      { messages: [asked], pending_card: null, running: true },
      { messages: [asked], pending_card: null, running: true },
      { messages: [asked, { role: 'assistant', id: 'a1', content: 'Set to car loan.' }], pending_card: null, running: false },
    ])
    vi.useFakeTimers({ toFake: ['setTimeout'] })
    const mounting = mount()
    await vi.advanceTimersByTimeAsync(10)
    const el = await mounting
    expect($(el, '.resumed')?.textContent).toContain('Still working')
    await vi.advanceTimersByTimeAsync(2100)   // still running
    expect($(el, '.resumed')).not.toBeNull()
    await vi.advanceTimersByTimeAsync(2100)   // done
    expect($(el, '.resumed')).toBeNull()
    expect(el.shadowRoot!.textContent).toContain('Set to car loan.')
  })

  it('Stop tells the server to end the turn', async () => {
    server([{ messages: [], pending_card: null, running: false }])
    const el = await mount()
    void el.send('hi')
    await tick(5)
    el.stop()
    await tick(5)
    const stop = calls.find((c) => c.url.endsWith('/agent/stop'))
    expect(stop && JSON.parse(stop.body!)).toEqual({ thread_id: 'th1' })
  })
})

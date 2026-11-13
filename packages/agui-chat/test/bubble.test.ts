import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import type { AguiEvent } from '../src/types'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const run = (...body: AguiEvent[]): AguiEvent[] => [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, ...body, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]
const text = (id: string, s: string): AguiEvent[] => [
  { type: 'TEXT_MESSAGE_START', messageId: id, role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: id, delta: s },
  { type: 'TEXT_MESSAGE_END', messageId: id }]
function sse(events: AguiEvent[]): Response {
  return new Response(new TextEncoder().encode(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')), { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}
let runs: number
function mockRuns(...list: AguiEvent[][]): void {
  runs = 0
  const queue = [...list]
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (!String(url).endsWith('/run')) return new Response(null, { status: 404 })
    runs++
    return sse(queue.shift() ?? run())
  }))
}
async function mount(opts: Record<string, unknown> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'bubble', typing: 'plain', 'persist-thread': 'off', lang: 'en', url: '/agent/run' })) el.setAttribute(k, v)
  el.options = opts
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement

beforeEach(() => { document.body.innerHTML = ''; localStorage.clear(); vi.spyOn(console, 'warn').mockImplementation(() => {}) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('bubble mode', () => {
  it('the launcher opens and closes the window', async () => {
    mockRuns()
    const el = await mount()
    const wrap = $(el, '.wrap'), fab = $(el, '.fab') as HTMLButtonElement
    expect(wrap.classList.contains('mode-bubble')).toBe(true)
    fab.click()
    expect(wrap.classList.contains('open')).toBe(true)
    expect(fab.getAttribute('aria-expanded')).toBe('true')
    fab.click()
    expect(wrap.classList.contains('open')).toBe(false)
    expect(wrap.classList.contains('closing')).toBe(true)           // shrinks back into the launcher
    await tick(260)
    expect(wrap.classList.contains('closing')).toBe(false)
  })

  it('marks an answer that arrives while closed, and clears it on open', async () => {
    mockRuns(run(...text('m', 'Hello.')))
    const el = await mount()
    await el.send('hi')
    await tick(5)
    const fab = $(el, '.fab')
    expect(fab.classList.contains('unread')).toBe(true)
    ;(fab as HTMLButtonElement).click()
    expect(fab.classList.contains('unread')).toBe(false)
  })

  it('shows the greeting once, until closed', async () => {
    mockRuns()
    const el = await mount({ greeting: 'Need help with the form?', greetingDelay: 0 })
    await tick(20)
    const greet = $(el, '.greet')
    expect(greet.hidden).toBe(false)
    expect(greet.textContent).toContain('Need help with the form?')
    ;($(el, '.greet-x') as HTMLButtonElement).click()
    expect(greet.hidden).toBe(true)
    const again = await mount({ greeting: 'Need help with the form?', greetingDelay: 0 })
    await tick(20)
    expect($(again, '.greet').hidden).toBe(true)                     // remembered
  })

  it('takes a custom launcher', async () => {
    mockRuns()
    const el = await mount({ render: { launcher: () => { const i = document.createElement('img'); i.alt = 'Anna'; return i } } })
    expect($(el, '.fab-own img').getAttribute('alt')).toBe('Anna')
    ;($(el, '.fab') as HTMLButtonElement).click()
    expect($(el, '.wrap').classList.contains('open')).toBe(true)
  })
})

describe('showCard', () => {
  it('shows any card without the agent and resolves with the answer', async () => {
    mockRuns()
    const el = await mount({ mode: 'inline' })
    el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
    await tick(5)
    const answer = el.showCard({ type: 'ask', question: 'Which loan?', allow_text: false, options: [{ id: 'auto', label: 'Car loan' }, { id: 'cash', label: 'Cash' }] })
    await tick()
    ;($(el, '.card .chip') as HTMLButtonElement).click()
    await expect(answer).resolves.toEqual({ answer: { ids: ['auto'] } })
    expect(runs).toBe(0)                                             // no run was started
  })
})

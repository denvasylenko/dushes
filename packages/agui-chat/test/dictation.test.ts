import { afterEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import type { AguiEvent } from '../src/types'

// Any chat action other than sending the composer stops dictation and drops what was dictated.

class FakeRecognition {
  static last: FakeRecognition | null = null
  lang = ''; continuous = false; interimResults = false
  onresult: ((e: unknown) => void) | null = null
  onerror: ((e: unknown) => void) | null = null
  onend: (() => void) | null = null
  aborted = false
  constructor() { FakeRecognition.last = this }
  start() {}
  stop() { setTimeout(() => this.onend?.()) }
  abort() { this.aborted = true }
  say(text: string, final = true) {
    this.onresult?.({ resultIndex: 0, results: { length: 1, 0: { isFinal: final, 0: { transcript: text } } } })
  }
}

const sse = (events: AguiEvent[]) => new Response(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(''),
  { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
const run = (...body: AguiEvent[]): AguiEvent[] => [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, ...body,
  { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]
const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))

let bodies: any[] // eslint-disable-line @typescript-eslint/no-explicit-any
function mockRuns(...runs: AguiEvent[][]) {
  bodies = []
  vi.stubGlobal('fetch', vi.fn(async (_u: string, init?: RequestInit) => {
    bodies.push(JSON.parse(String(init?.body)))
    return sse(runs.shift() ?? run())
  }))
}

async function mount(): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off' })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, sel: string) => el.shadowRoot!.querySelector(sel) as HTMLElement

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = '' })

function dictate(el: AguiChatElement, typed: string, said: string) {
  const input = $(el, 'textarea') as HTMLTextAreaElement
  input.value = typed
  $(el, '.mic').click()
  FakeRecognition.last!.say(said, false)
  return input
}

describe('dictation ends with any chat action', () => {
  it('a starter chip: the chip is sent, the dictated words are dropped, late results ignored', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition)
    mockRuns(run())
    const el = await mount()
    el.options = { starters: ['Book a haircut'] }
    await tick()
    const input = dictate(el, '', 'which barber')
    const rec = FakeRecognition.last!
    ;(el.shadowRoot!.querySelector('.chip') as HTMLButtonElement).click()
    await tick(5)
    expect(rec.aborted).toBe(true)
    expect($(el, '.mic').classList.contains('on')).toBe(false)
    rec.say('which barber is free')               // arrives after the chip: ignored
    expect(input.value).toBe('')
    expect(bodies[0].messages.at(-1).content).toBe('Book a haircut')
  })

  it('Skip on a card: dictation stops and only the typed text stays', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition)
    const ask = { type: 'CUSTOM', name: 'on_interrupt',
      value: JSON.stringify({ type: 'confirm', card_id: 'k', title: 'Send?', message: 'Sure?' }) }
    mockRuns(run(ask), run())
    const el = await mount()
    el.use({ name: 'test', renderers: { confirm: (_it, c) => {
      const b = document.createElement('button'); b.className = 'skip'; b.onclick = () => c.resolve({ accepted: false }); return b
    } } })
    await el.send('go')
    await tick(5)
    const input = dictate(el, 'Note:', 'and also the')
    expect(input.value).toBe('Note: and also the')
    ;($(el, '.skip') as HTMLButtonElement).click()
    await tick(5)
    expect(FakeRecognition.last!.aborted).toBe(true)
    expect($(el, '.mic').classList.contains('on')).toBe(false)
    expect(input.value).toBe('Note:')
  })

  it('New chat stops dictation', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition)
    mockRuns()
    const el = await mount()
    dictate(el, '', 'hello there')
    el.reset()
    expect(FakeRecognition.last!.aborted).toBe(true)
    expect(($(el, 'textarea') as HTMLTextAreaElement).value).toBe('')
  })
})

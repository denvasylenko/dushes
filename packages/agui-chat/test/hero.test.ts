import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import type { AguiEvent, Plugin } from '../src/types'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const agentOf = (events: AguiEvent[]) => ({ run: () => ({ subscribe: (o: { next: (e: AguiEvent) => void; complete: () => void }) => {
  setTimeout(() => { for (const e of events) o.next(e); o.complete() })
  return { unsubscribe: () => {} }
} }) })
const reply: AguiEvent[] = [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, { type: 'TEXT_MESSAGE_START', messageId: 'a', role: 'assistant' },
  { type: 'TEXT_MESSAGE_CONTENT', messageId: 'a', delta: 'Found it.' }, { type: 'TEXT_MESSAGE_END', messageId: 'a' }, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]

function phone(on: boolean) {
  vi.stubGlobal('matchMedia', (q: string) => ({ matches: q.includes('min-width: 760px') ? !on : false, addEventListener() {}, removeEventListener() {} }))
}
async function mount(extra?: Plugin): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'hero', typing: 'plain', lang: 'en', 'persist-thread': 'off', placeholder: 'Bar Centrale, Pescara' })) el.setAttribute(k, v)
  if (extra) el.use(extra)
  document.body.appendChild(el)
  await tick()
  return el
}
const wrap = (el: AguiChatElement) => el.shadowRoot!.querySelector('.wrap') as HTMLElement

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('hero mode', () => {
  it('is only the field until the first message, then grows into the chat', async () => {
    phone(false)
    const el = await mount()
    expect(wrap(el).classList.contains('mode-hero')).toBe(true)
    expect(wrap(el).classList.contains('open')).toBe(false)
    expect(el.shadowRoot!.querySelector('.empty')).toBeNull()                  // no empty state: the page around it is
    expect((el.shadowRoot!.querySelector('textarea') as HTMLTextAreaElement).placeholder).toBe('Bar Centrale, Pescara')
    const opened = vi.fn()
    el.addEventListener('agui:open', opened)
    el.agent = agentOf(reply)
    await el.send('Bar Centrale, Pescara')
    await tick(5)
    expect(wrap(el).classList.contains('open')).toBe(true)
    expect(opened).toHaveBeenCalledTimes(1)
    expect(el.shadowRoot!.textContent).toContain('Found it.')
  })

  it('setPlaceholder changes the hint (a language switch)', async () => {
    phone(false)
    const el = await mount()
    el.setPlaceholder('Bar Centrale, Pescara (IT)')
    expect((el.shadowRoot!.querySelector('textarea') as HTMLTextAreaElement).placeholder).toBe('Bar Centrale, Pescara (IT)')
  })

  it('on a phone closes back to the field and keeps the conversation', async () => {
    phone(true)
    const el = await mount()
    el.agent = agentOf(reply)
    await el.send('hi')
    await tick(5)
    const closed = vi.fn()
    el.addEventListener('agui:close', closed)
    ;(el.shadowRoot!.querySelector('.close') as HTMLButtonElement).click()
    expect(wrap(el).classList.contains('open')).toBe(false)
    expect(closed).toHaveBeenCalledTimes(1)
    expect(el.shadowRoot!.textContent).toContain('Found it.')                   // the conversation stays
  })

  it('a turn still running after a reload reopens it', async () => {
    phone(true)
    const restore: Plugin = { name: 'host', restore: async () => ({ messages: [{ id: 'u', role: 'user', content: 'hi' }], running: true }) }
    const el = await mount(restore)
    await tick(10)
    expect(wrap(el).classList.contains('open')).toBe(true)
  })
})

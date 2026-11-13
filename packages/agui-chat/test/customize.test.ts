import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import { PART_NAMES } from '../src/parts'
import { reactSlot } from '../src/react'
import { themeCss } from '../src/themes'
import type { AguiEvent } from '../src/types'

function sse(events: AguiEvent[]): Response {
  return new Response(new TextEncoder().encode(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')),
    { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}
const run = (...body: AguiEvent[]): AguiEvent[] => [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, ...body, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]
const text = (id: string, s: string): AguiEvent[] => [
  { type: 'TEXT_MESSAGE_START', messageId: id, role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: id, delta: s },
  { type: 'TEXT_MESSAGE_END', messageId: id }]
const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
function mockRuns(...runs: (AguiEvent[] | 'fail')[]): void {
  const queue = [...runs]
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (!String(url).endsWith('/run')) return new Response(null, { status: 404 })
    const next = queue.shift() ?? run()
    return next === 'fail' ? new Response('boom', { status: 500 }) : sse(next)
  }))
}
async function mount(opts: Record<string, unknown> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off', lang: 'en', url: '/agent/run' })) el.setAttribute(k, v)
  el.options = opts
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement
const parts = (el: AguiChatElement, s: string) => ($(el, s)?.getAttribute('part') ?? '').split(' ')

beforeEach(() => { document.body.innerHTML = ''; vi.spyOn(console, 'warn').mockImplementation(() => {}) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('parts on every element', () => {
  it('names the chrome and card content, also elements added later', async () => {
    mockRuns(run({ type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'ask', card_id: 'q', question: 'Which?', allow_text: false,
      options: [{ id: 'a', label: 'A', description: 'first' }, { id: 'b', label: 'B' }] }) }), run(...text('m', 'Ok.')))
    const el = await mount()
    el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
    await tick(5)                                                     // the empty chat is redrawn after use()
    expect(parts(el, '.head')).toContain('header')
    expect(parts(el, '.empty')).toContain('empty')
    expect(parts(el, '.box textarea')).toContain('input')
    await el.send('go')
    await tick(5)
    expect(parts(el, '.card-q')).toContain('card-question')
    expect(parts(el, '.opt')).toEqual(expect.arrayContaining(['chip', 'option']))
    ;($(el, '.opt') as HTMLButtonElement).click()
    await tick(5)
    expect(parts(el, '.card .ok-line')).toContain('result')        // added after the answer
    expect(PART_NAMES).toEqual(expect.arrayContaining(['calendar-day', 'button-primary', 'review-issue', 'receipt']))
  })
})

describe('component tokens and icons', () => {
  it('accepts component tokens as short keys', () => {
    const css = themeCss({ tokens: { 'card-bg': '#fafafa', 'chip-radius': '6px', 'bubble-user-bg': '#e8f0ff' } })
    expect(css).toContain('--agui-card-bg: #fafafa;')
    expect(css).toContain('--agui-chip-radius: 6px;')
    expect(css).toContain('--agui-bubble-user-bg: #e8f0ff;')
  })

  it('replaces built-in icons', async () => {
    const el = await mount({ icons: { logo: '<svg data-x="logo"></svg>', send: '<svg data-x="send"></svg>' } })
    expect($(el, '.logo svg').dataset.x).toBe('logo')
    expect($(el, '.fab svg').dataset.x).toBe('logo')
    expect($(el, '.fab .fab-label')).not.toBeNull()
    expect($(el, '.send svg').dataset.x).toBe('send')
  })
})

describe('slots', () => {
  it('replaces the empty chat, the header and the composer', async () => {
    const el = await mount({ render: {
      empty: (d: { title: string }) => { const x = document.createElement('div'); x.className = 'mine'; x.textContent = `Hi from ${d.title}`; return x },
      header: (d: { title: string }) => { const x = document.createElement('div'); x.className = 'my-head'; x.textContent = d.title; return x },
      composer: (chat: AguiChatElement) => { const b = document.createElement('button'); b.className = 'my-send'; b.onclick = () => void chat.send('hello'); return b },
    }, title: 'Shop' })
    expect($(el, '.empty .mine').textContent).toBe('Hi from Shop')
    expect($(el, '.head .my-head').textContent).toBe('Shop')
    expect($(el, '.box')).toBeNull()                                   // the default composer is gone
    expect($(el, '.foot .my-send')).not.toBeNull()
  })

  it('renders answers with the host markdown and component, user bubbles and suggestions', async () => {
    mockRuns(run(...text('m1', 'Hello **there**'), { type: 'CUSTOM', name: 'suggestions', value: { items: ['Next'] } } as AguiEvent))
    const markdown = vi.fn((t: string) => `<em>${t}</em>`)
    const el = await mount({ render: {
      markdown,
      assistant: (t: string) => { const x = document.createElement('article'); x.className = 'answer'; x.textContent = t.toUpperCase(); return x },
      user: (t: string) => { const x = document.createElement('span'); x.className = 'me'; x.textContent = `> ${t}`; return x },
      suggestions: (items: string[]) => { const x = document.createElement('nav'); x.className = 'next'; x.textContent = items.join('|'); return x },
    } })
    await el.send('hi')
    await tick(5)
    expect(markdown).toHaveBeenCalled()
    expect($(el, '.msg.ai .answer').textContent).toBe('HELLO **THERE**')
    expect($(el, '.msg.me .me').textContent).toBe('> hi')
    expect($(el, '.quick .next').textContent).toBe('Next')
  })

  it('a failing slot falls back to the default, and errors can be the host own', async () => {
    mockRuns('fail')
    const el = await mount({ render: {
      user: () => { throw new Error('bad') },
      error: (d: { text: string; retry: () => void }) => { const x = document.createElement('div'); x.className = 'oops'; x.textContent = d.text; return x },
    } })
    await el.send('hi')
    await tick(10)
    expect($(el, '.msg.me').textContent).toBe('hi')                   // default bubble
    expect($(el, '.error .oops').textContent).toBeTruthy()
    expect(console.warn).toHaveBeenCalled()
  })

  it('reactSlot mounts a component through the host createRoot', () => {
    const render = vi.fn()
    const createRoot = vi.fn(() => ({ render, unmount: () => {} }))
    const Comp = () => null
    const slot = reactSlot(createRoot, Comp)
    const chat = {} as AguiChatElement
    const el = slot('hello', chat)
    expect(el.className).toBe('react-slot')
    expect(createRoot).toHaveBeenCalledWith(el)
    expect(render.mock.calls[0][0].props).toEqual({ data: 'hello', args: ['hello'], chat })
  })
})

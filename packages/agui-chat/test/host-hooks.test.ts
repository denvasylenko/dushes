import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide, type FormguideOptions } from '../src/formguide/index'
import type { AguiEvent, Plugin } from '../src/types'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const agentOf = (events: AguiEvent[]) => ({ run: () => ({ subscribe: (o: { next: (e: AguiEvent) => void; complete: () => void }) => {
  setTimeout(() => { for (const e of events) o.next(e); o.complete() })
  return { unsubscribe: () => {} }
} }) })
const start: AguiEvent = { type: 'RUN_STARTED', threadId: 't', runId: 'r' }
const end: AguiEvent = { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }
const say = (id: string, text: string): AguiEvent[] => [{ type: 'TEXT_MESSAGE_START', messageId: id, role: 'assistant' },
  { type: 'TEXT_MESSAGE_CONTENT', messageId: id, delta: text }, { type: 'TEXT_MESSAGE_END', messageId: id }]

async function mount(opts: Partial<FormguideOptions> = {}, extra?: Plugin): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
  const plugin = formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async (ch) => ({ props: {}, state: ch }), ...opts })
  delete plugin.restore
  el.use(plugin)
  if (extra) el.use(extra)
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement | null

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('host hooks', () => {
  it('removeMessage takes back a shown answer (a host "cut")', async () => {
    const el = await mount()
    el.agent = agentOf([start, ...say('m1', 'Let me check that.'), ...say('m2', 'Found it.'), end])
    await el.send('hi')
    await tick(5)
    expect(el.shadowRoot!.textContent).toContain('Let me check that.')
    expect(el.removeMessage('m1')).toBe(true)
    expect(el.shadowRoot!.textContent).not.toContain('Let me check that.')
    expect(el.shadowRoot!.textContent).toContain('Found it.')
    expect(el.removeMessage('nope')).toBe(false)
  })

  it('onAction handles a display card button without a message; updateCard redraws it in place', async () => {
    const onAction = vi.fn(async (card: Record<string, unknown>, action: { id: string }, chat: AguiChatElement) => {
      if (action.id !== 'save') return false
      chat.updateCard(String(card.card_id), { blocks: [{ type: 'steps', title: 'Done', items: [{ label: 'Opening hours', done: true }] }] })
      return true
    })
    const el = await mount({ onAction: onAction as unknown as FormguideOptions['onAction'] })
    el.agent = agentOf([start, { type: 'CUSTOM', name: 'card', value: { type: 'blocks', name: 'todo', card_id: 'todo-1', blocks: [
      { type: 'steps', title: '1 step left', items: [{ label: 'Opening hours' }] },
      { type: 'buttons', items: [{ id: 'save', label: 'Save hours', style: 'primary' }, { id: 'other', label: 'Ask about it' }] }] } }, end])
    await el.send('what is left?')
    await tick(5)
    const sends = vi.spyOn(el, 'send')
    ;($(el, '.bk .btn.pri') as HTMLButtonElement).click()
    await tick(5)
    expect(onAction).toHaveBeenCalledWith(expect.objectContaining({ card_id: 'todo-1' }), { id: 'save', label: 'Save hours', values: {} }, el)
    expect(sends).not.toHaveBeenCalled()                                    // handled: no message
    expect($(el, '[data-card-id="todo-1"] .bk-steps')!.textContent).toContain('Done')   // redrawn in place
    expect(el.shadowRoot!.querySelectorAll('[data-card-id="todo-1"]')).toHaveLength(1)
  })

  it('a restore can follow the running turn: its answer goes on as a live run', async () => {
    async function* follow(): AsyncIterable<AguiEvent> {
      yield start
      yield { type: 'TEXT_MESSAGE_START', messageId: 'a', role: 'assistant' }
      yield { type: 'TEXT_MESSAGE_CONTENT', messageId: 'a', delta: 'Half of the answer, ' }
      await tick(10)
      yield { type: 'TEXT_MESSAGE_CONTENT', messageId: 'a', delta: 'and the rest after the reload.' }
      yield { type: 'TEXT_MESSAGE_END', messageId: 'a' }
      yield end
    }
    const restore: Plugin = { name: 'host', restore: async () => ({ messages: [{ id: 'u', role: 'user', content: 'Tell me' }], follow }) }
    const el = await mount({}, restore)
    await tick(40)
    expect(el.shadowRoot!.textContent).toContain('Tell me')
    expect(el.shadowRoot!.textContent).toContain('Half of the answer, and the rest after the reload.')
    expect(el.busy).toBe(false)
  })

  it('tells the page which fields a card filled: agui:applied', async () => {
    const el = await mount()
    const seen: unknown[] = []
    el.addEventListener('agui:applied', (e) => seen.push((e as CustomEvent).detail))
    const answer = el.showCard({ type: 'blocks', blocks: [{ type: 'buttons', items: [{ id: 'yes', label: 'Yes', style: 'primary', fills: { barber: 'maria' } }] }] })
    await tick()
    ;($(el, '.btn.pri') as HTMLButtonElement).click()
    await answer
    expect(seen).toEqual([{ fields: ['barber'], values: { barber: 'maria' }, undo: false }])
    ;($(el, '.ok-line .btn') as HTMLButtonElement).click()                   // Undo
    await tick(5)
    expect(seen[1]).toMatchObject({ fields: ['barber'], undo: true })
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import type { AguiEvent } from '../src/types'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
async function mount(): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
  el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]

const BARBER = { type: 'blocks', name: 'barber_match', blocks: [
  { type: 'title', text: 'Is this your barber?' },
  { type: 'place', title: 'Maria', subtitle: 'Arbat 12', rating: 4.9, image: 'javascript:alert(1)' },
  { type: 'row', label: 'Next slot', value: 'Today, 16:30' },
  { type: 'row', label: 'Haircut', value: 'from 1 500' },
  { type: 'choice', name: 'slot', options: ['16:30', '18:00'] },
  { type: 'swatches', name: 'palette', items: [{ id: 'calm', label: 'Calm', colors: ['#000', 'red;} *{x'] }] },
  { type: 'field', name: 'wish', label: 'A wish' },
  { type: 'carousel', items: [] },
  { type: 'buttons', items: [{ id: 'yes', label: 'Yes, book her', style: 'primary' }, { id: 'no', label: 'Another' }] },
] }

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('cards from blocks', () => {
  it('draws the blocks in order, groups rows and skips what it does not know', async () => {
    const el = await mount()
    void el.showCard(structuredClone(BARBER))
    await tick()
    expect($(el, '.card .bk-title').textContent).toContain('Is this your barber?')
    expect($(el, '.bk-place .bk-strong').textContent).toBe('Maria')
    expect($(el, '.bk-place img')).toBeNull()                               // javascript: is not an image
    expect($(el, '.bk-rating').textContent).toContain('4.9')
    expect($$(el, '.bk-list')).toHaveLength(1)                              // two rows, one grouped list
    expect($$(el, '.bk-list .bk-row')).toHaveLength(2)
    expect($$(el, '.bk .chip').map((b) => b.textContent)).toEqual(['16:30', '18:00'])   // plain strings become options
    expect(($$(el, '.bk-sw-c i')[1]).style.background).toBe('transparent')  // only hex colours from data
    expect($(el, '.btn.pri').textContent).toBe('Yes, book her')
  })

  it('answers with the button and the values, and folds into its result line', async () => {
    const el = await mount()
    const answer = el.showCard(structuredClone(BARBER))
    await tick()
    $$(el, '.bk .chip')[1].click()
    $(el, '.bk-sw').click()
    const wish = $(el, '.bk-field input') as HTMLInputElement
    wish.value = 'Shorter'
    wish.dispatchEvent(new Event('input'))
    $(el, '.btn.pri').click()
    await expect(answer).resolves.toEqual({ action: 'yes', label: 'Yes, book her', values: { slot: '18:00', palette: 'calm', wish: 'Shorter' } })
    expect($(el, '.card .ok-line').textContent).toContain('Yes, book her')
    expect($(el, '.card .btn')).toBeNull()
  })

  it('a button with fills fills the form in one tap, with Undo, and answers with the new config', async () => {
    const applyChanges = vi.fn(async (ch: Record<string, unknown>) => ({ props: {}, state: ch }))
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
    el.use(formguide({ getState: () => ({ config: { props: {}, state: { barber: null } }, jsx_hash: 'h' }), applyChanges }))
    document.body.appendChild(el)
    await tick()
    const answer = el.showCard({ type: 'blocks', name: 'barber_match', fill_meta: { barber: { label: 'Barber', previous: null } }, blocks: [
      { type: 'title', text: 'Is this your barber?' },
      { type: 'buttons', items: [{ id: 'yes', label: 'Yes, book Maria', style: 'primary', fills: { barber: { id: 'maria', name: 'Maria' } } }, { id: 'no', label: 'Another' }] }] })
    await tick()
    $(el, '.btn.pri').click()
    await expect(answer).resolves.toMatchObject({ action: 'yes', label: 'Yes, book Maria', config: { state: { barber: { id: 'maria', name: 'Maria' } } } })
    expect(applyChanges).toHaveBeenCalledWith({ barber: { id: 'maria', name: 'Maria' } })
    expect($(el, '.card .ok-line').textContent).toContain('Yes, book Maria')
    expect(($(el, '.card .ok-line .btn') as HTMLButtonElement).textContent).toBe('Undo')
  })

  it('shows no step for the tool that made a card from blocks', async () => {
    const el = await mount()
    el.agent = { run: () => ({ subscribe: (o: { next: (e: AguiEvent) => void; complete: () => void }) => {
      setTimeout(() => { for (const e of [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' },
        { type: 'TOOL_CALL_START', toolCallId: 'c', toolCallName: 'show_barber_match' }, { type: 'TOOL_CALL_END', toolCallId: 'c' },
        { type: 'CUSTOM', name: 'on_interrupt', value: { ...BARBER, card_id: 'b1' } }, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }] as AguiEvent[]) o.next(e); o.complete() })
      return { unsubscribe: () => {} }
    } }) }
    await el.send('my usual barber')
    await tick(5)
    expect($(el, '.card .bk')).not.toBeNull()
    expect($$(el, '.steps').filter((s) => !s.hidden)).toHaveLength(0)   // the card shows what the tool did
  })

  it('shows a display card from the server; its links act and empty ones are left out', async () => {
    const el = await mount()
    const card = { type: 'blocks', name: 'visit', blocks: [
      { type: 'stat', value: 'Fri, 16:30', label: 'Haircut', tone: 'ok' },
      { type: 'links', items: [
        { kind: 'call', label: 'Call', value: '+7 (495) 000-00-00' },
        { kind: 'route', label: 'Route', value: 'Arbat 12' },
        { kind: 'web', label: 'Site', value: 'javascript:alert(1)' },
        { kind: 'call', label: 'No phone', value: '' },
        { kind: 'calendar', label: 'Add to calendar', value: { title: 'Haircut', start: '2026-11-20T16:30:00', minutes: 45 } }] },
    ] }
    el.agent = { run: () => ({ subscribe: (o: { next: (e: AguiEvent) => void; complete: () => void }) => {
      setTimeout(() => { for (const e of [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, { type: 'CUSTOM', name: 'card', value: card },
        { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }] as AguiEvent[]) o.next(e); o.complete() })
      return { unsubscribe: () => {} }
    } }) }
    await el.send('how do I get there')
    await tick(5)
    expect($(el, '.card.bk .bk-big').textContent).toBe('Fri, 16:30')
    const links = $$(el, '.bk-link')
    expect(links.map((a) => a.textContent)).toEqual(['Call', 'Route', 'Site', 'Add to calendar'])   // "No phone" is gone
    expect(links[0].getAttribute('href')).toBe('tel:+74950000000')
    expect(links[1].getAttribute('href')).toContain('maps.apple.com/?q=Arbat%2012')
    expect(links[2].tagName).toBe('BUTTON')                                  // javascript: never becomes a link
    expect(links[3].getAttribute('href')).toMatch(/^data:text\/calendar/)
    expect(decodeURIComponent(links[3].getAttribute('href')!)).toContain('DTSTART:')
  })
})

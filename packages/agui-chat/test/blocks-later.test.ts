// The one-script build loads the card blocks on demand (agui-chat.blocks.js): a card is shown at once as its empty
// element and filled when the file arrives. Here the loader is replaced by one the test releases by hand.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import type { Blocks } from '../src/blocks-loader'
import { blocksCard, formguide } from '../src/formguide/index'
import type { RendererContext } from '../src/types'

const load = vi.hoisted(() => ({ ready: null as Blocks | null, pending: [] as { ok: () => void; fail: () => void }[] }))
vi.mock('#blocks-loader', async () => {
  const real = await import('../src/formguide/blocks')
  const b: Blocks = { blocksCard: real.blocksCard, blocksRenderer: real.blocksRenderer }
  return {
    blocksNow: () => load.ready,
    loadBlocks: () => load.ready ? Promise.resolve(load.ready) : new Promise<Blocks>((ok, fail) => {
      load.pending.push({ ok: () => ok(load.ready = b), fail: () => fail(new Error('agui-chat.blocks.js')) })
    }),
  }
})
const arrive = async (ok = true) => { const p = load.pending.splice(0); p.forEach((x) => (ok ? x.ok() : x.fail())); await tick() }

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

beforeEach(() => { document.body.innerHTML = ''; load.ready = null; load.pending = []
  vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('cards from blocks, loaded on demand', () => {
  it('shows the card at once, fills it when the blocks arrive, and it answers as usual', async () => {
    const el = await mount()
    const answer = el.showCard({ type: 'blocks', blocks: [{ type: 'title', text: 'Your barber?' },
      { type: 'buttons', items: [{ id: 'yes', label: 'Yes', style: 'primary' }] }] })
    await tick()
    expect($(el, '.card.bk-wait[aria-busy="true"]')).not.toBeNull()   // its room kept while the file loads
    expect($(el, '.bk-title')).toBeNull()
    await arrive()
    expect($(el, '.bk-title').textContent).toContain('Your barber?')
    expect($(el, '[aria-busy]')).toBeNull()
    $(el, '.btn.pri').click()
    expect(await answer).toEqual({ action: 'yes', label: 'Yes', values: {} })
  })

  it('blocksCard returns its element at once and draws into that same element later', async () => {
    const el = await mount()
    const c = { chat: el, t: el.t.bind(el), resolve: () => {}, flags: {}, restored: false } as unknown as RendererContext
    const card = blocksCard({ name: 'mine', blocks: [{ type: 'row', label: 'Next slot', value: '16:30' }] }, c, null)
    expect(card.getAttribute('part')).toBe('blocks blocks-mine')
    expect(card.children).toHaveLength(0)
    await arrive()
    expect(card.querySelector('.bk-row .bk-value')!.textContent).toBe('16:30')
    // once here, the next card is drawn at once
    expect(blocksCard({ blocks: [{ type: 'divider' }] }, c, null).querySelector('.bk-hr')).not.toBeNull()
  })

  it('a file that fails to load leaves Try again, which loads it again', async () => {
    const el = await mount()
    void el.showCard({ type: 'picker', title: 'Book', groups: [{ name: 'day', label: 'Day', options: ['Mon'] }] })
    await tick()
    await arrive(false)
    expect($(el, '.card .err-line').textContent).toBe('Something went wrong.')
    ;($(el, '.card .btn.link') as HTMLButtonElement).click()
    expect($(el, '.card[aria-busy="true"]')).not.toBeNull()
    await arrive()
    expect($(el, '.card .bk-title').textContent).toContain('Book')
    expect($(el, '.card').textContent).not.toContain('Something went wrong.')
  })
})

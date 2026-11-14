import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import type { AguiEvent } from '../src/types'
import { hoursText } from '../src/formguide/blocks-base'

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
    const links = $$(el, '.bk-links > .bk-link, .bk-cal > .bk-link')
    expect(links.map((a) => a.textContent)).toEqual(['Call', 'Route', 'Site', 'Add to calendar'])   // "No phone" is gone
    expect(links[0].getAttribute('href')).toBe('tel:+74950000000')
    expect(links[1].getAttribute('href')).toContain('maps.apple.com/?q=Arbat%2012')
    expect(links[2].tagName).toBe('BUTTON')                                  // javascript: never becomes a link
    // "Add to calendar" opens its choices in place: Apple (.ics), Google, Outlook, all in local time
    const menu = $(el, '.bk-menu')
    expect(menu.hidden).toBe(true)
    links[3].click()
    expect(menu.hidden).toBe(false)
    expect(links[3].getAttribute('aria-expanded')).toBe('true')
    const [apple, google, outlook] = [...menu.querySelectorAll('a')]
    expect([apple, google, outlook].map((a) => a.textContent)).toEqual(['Apple Calendar', 'Google Calendar', 'Outlook'])
    expect(decodeURIComponent(apple.getAttribute('href')!)).toContain('DTSTART:')
    expect(apple.getAttribute('download')).toBe('Add to calendar.ics')
    expect(new URL(google.getAttribute('href')!).searchParams.get('dates')).toBe('20261120T163000/20261120T171500')
    const o = new URL(outlook.getAttribute('href')!).searchParams
    expect([o.get('subject'), o.get('startdt'), o.get('enddt')]).toEqual(['Haircut', '2026-11-20T16:30:00', '2026-11-20T17:15:00'])
  })
})

const BOOKING = { type: 'picker', title: 'Book a table', need: 'Choose: {x}', submit: { label: 'Book' },
  groups: [
    { name: 'day', label: 'Day', options: [{ id: 'fri', label: 'Fri' }, { id: 'sat', label: 'Sat', off: 'Closed' }], more: { label: 'Other days', options: [{ id: 'sun', label: 'Sun' }] } },
    { name: 'time', label: 'Time' },
    { name: 'people', label: 'People', options: ['2', '4'], value: '2' },
  ],
  depends: { time: { on: 'day', options: { fri: ['18:00', '20:00'], sun: ['12:00'] } } },
  fields: [{ name: 'phone', label: 'Phone', input: 'tel', required: true }] }

describe('a picker card', () => {
  it('one choice per group; times follow the day; the button waits and says what is missing; answers with the values', async () => {
    const el = await mount()
    const answer = el.showCard(structuredClone(BOOKING))
    await tick()
    const group = (label: string) => $$(el, '.bk-group').find((g) => g.querySelector('.bk-cap')!.textContent === label)!
    const chips = (label: string) => [...group(label).querySelectorAll<HTMLButtonElement>('.chip')]
    const book = $(el, '.btn.pri') as HTMLButtonElement
    const need = $(el, '.bk-need')
    expect($(el, '.bk-title').textContent).toContain('Book a table')
    expect(book.textContent).toBe('Book')
    expect(book.disabled).toBe(true)
    expect(need.textContent).toBe('Choose: Day, Time, Phone')                // People has a default
    expect(chips('Day')[1].disabled).toBe(true)                               // closed
    expect(chips('Time')).toHaveLength(0)
    chips('Day')[2].click()                                                    // "Other days" opens the rest in place
    expect(chips('Day').map((b) => b.textContent)).toEqual(['Fri', 'Sat', 'Sun'])
    chips('Day')[2].click()
    expect(chips('Time').map((b) => b.textContent)).toEqual(['12:00'])
    chips('Day')[0].click()
    expect(chips('Day').filter((b) => b.classList.contains('on')).map((b) => b.textContent)).toEqual(['Fri'])   // one per group
    expect(chips('Time').map((b) => b.textContent)).toEqual(['18:00', '20:00'])
    chips('Time')[1].click()
    expect(need.textContent).toBe('Choose: Phone')
    const phone = $(el, 'input[type=tel]') as HTMLInputElement
    phone.value = '+1 555 0100'; phone.dispatchEvent(new Event('input'))
    expect(book.disabled).toBe(false)
    expect(need.textContent).toBe('')
    book.click()
    expect(await answer).toEqual({ action: 'submit', label: 'Book', values: { day: 'fri', time: '20:00', people: '2', phone: '+1 555 0100' } })
  })
})

describe('opening hours and a site preview', () => {
  it('hours: a preset in one tap, days as chips, a second pair; the button answers with the list', async () => {
    const el = await mount()
    const answer = el.showCard({ type: 'blocks', blocks: [
      { type: 'hours', name: 'hours', label: 'Hours' },
      { type: 'buttons', items: [{ id: 'save', label: 'Save', style: 'primary' }] }] })
    await tick()
    const save = $(el, '.btn.pri') as HTMLButtonElement
    expect(save.disabled).toBe(true)                                          // no days chosen yet
    expect($(el, '.bk-need').textContent).toBe('Choose: Hours')
    const presets = $$(el, '.bk-hours > .chips .chip')
    expect(presets.map((b) => b.textContent)).toEqual(['Mon\u2013Fri 09:00\u201318:00', 'Mon\u2013Sun 12:00\u201323:00'])
    presets[0].click()
    expect(save.disabled).toBe(false)
    const pairDays = () => $$(el, '.bk-pair')[0].querySelectorAll<HTMLButtonElement>('.chip')
    expect([...pairDays()].filter((b) => b.classList.contains('on')).map((b) => b.textContent)).toEqual(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])
    pairDays()[4].click()                                                       // Friday off
    ;($(el, '.bk-add') as HTMLButtonElement).click()                            // a second pair: Saturday 10-14
    const second = $$(el, '.bk-pair')[1]
    ;(second.querySelectorAll<HTMLButtonElement>('.chip')[5]).click()
    const [from, to] = [...second.querySelectorAll<HTMLInputElement>('input[type=time]')]
    from.value = '10:00'; from.dispatchEvent(new Event('input'))
    to.value = '14:00'; to.dispatchEvent(new Event('input'))
    save.click()
    const v = await answer as { values: { hours: unknown } }
    expect(v.values.hours).toEqual([{ days: [0, 1, 2, 3], from: '09:00', to: '18:00' }, { days: [5], from: '10:00', to: '14:00' }])
    expect(hoursText(v.values.hours as never)).toBe('Mon\u2013Thu 09:00\u201318:00; Sat 10:00\u201314:00')
  })

  it('preview: a page drawn at its own width, view only, opens on tap; no web address, no block', async () => {
    const el = await mount()
    void el.showCard({ type: 'blocks', blocks: [
      { type: 'preview', src: 'https://example.com/site', href: 'https://example.com/site', title: 'Your site', ratio: '9:16' },
      { type: 'preview', src: 'javascript:alert(1)' }] })
    await tick()
    const box = $$(el, '.bk-preview')
    expect(box).toHaveLength(1)
    expect(box[0].tagName).toBe('A')
    expect(box[0].classList.contains('tall')).toBe(true)
    const frame = box[0].querySelector('iframe')!
    expect(frame.getAttribute('sandbox')).toBe('allow-scripts')
    expect(frame.style.width).toBe('390px')
  })
})

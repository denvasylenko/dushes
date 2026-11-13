import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide, type FormguideOptions } from '../src/formguide/index'
import { formatValue, optionsLook } from '../src/formguide/pickers'
import type { AguiEvent } from '../src/types'

function sse(events: AguiEvent[]): Response {
  const text = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
  return new Response(new TextEncoder().encode(text), { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}
const run = (...body: AguiEvent[]): AguiEvent[] => [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, ...body, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]
const text = (id: string, s: string): AguiEvent[] => [
  { type: 'TEXT_MESSAGE_START', messageId: id, role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: id, delta: s },
  { type: 'TEXT_MESSAGE_END', messageId: id }]
const interrupt = (v: unknown): AguiEvent => ({ type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify(v) })
const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))

let bodies: any[] // eslint-disable-line @typescript-eslint/no-explicit-any
let fetches: { url: string; body: any }[] // eslint-disable-line @typescript-eslint/no-explicit-any
function mockRuns(...runs: AguiEvent[][]): void {
  bodies = []; fetches = []
  const queue = [...runs]
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const body = init?.body ? JSON.parse(String(init.body)) : null
    fetches.push({ url, body })
    if (String(url).endsWith('/run')) { bodies.push(body); return sse(queue.shift() ?? run()) }
    return new Response(null, { status: String(url).includes('/threads/') ? 404 : 204 })
  }))
}

async function chatWith(first: AguiEvent[], opts: Partial<FormguideOptions> = {}, state: Record<string, unknown> = {}) {
  mockRuns(first, run(...text('m9', 'Done.')))
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off', lang: 'en', url: '/agent/run' })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  const st = { config: { props: {}, state: { ...state } as Record<string, unknown> }, jsx_hash: 'h', form_id: 'f', ui: null }
  const applyChanges = vi.fn(async (c: Record<string, unknown>) => { Object.assign(st.config.state, c); return { ...st.config } })
  const onDirective = vi.fn()
  el.use(formguide({ getState: () => st, applyChanges, onDirective, ...opts }))
  await el.send('go')
  await tick(5)
  return { el, applyChanges, onDirective, st }
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]
const resume = () => bodies[1]?.forwardedProps?.command?.resume

beforeEach(() => { document.body.innerHTML = ''; vi.spyOn(console, 'warn').mockImplementation(() => {}) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('card kit: values and looks', () => {
  it('formats by the field role', () => {
    expect(formatValue('123456', 'text', 'en')).toBe('123456')
    expect(formatValue('1500000', 'number', 'en')).toBe('1,500,000')
    expect(formatValue('1990-05-31', 'date', 'en')).toBe('May 31, 1990')
    expect(formatValue('1500000', undefined, 'en')).toBe('1,500,000')
  })

  it('picks the look from the options', () => {
    const a = { id: 'a', label: 'A' }
    expect(optionsLook([a, { id: 'b', label: 'B' }])).toBe('chips')
    expect(optionsLook([{ ...a, description: 'x' }, { id: 'b', label: 'B' }])).toBe('details')
    expect(optionsLook([{ ...a, attrs: { M: '1' } }, { id: 'b', label: 'B', attrs: { M: '2' } }])).toBe('compare')
    expect(optionsLook(Array.from({ length: 13 }, (_, i) => ({ id: String(i), label: `O${i}` })))).toBe('search')
  })

  it('sends its capabilities with every run', async () => {
    await chatWith(run(...text('m1', 'Hi.')))
    expect(bodies[0].forwardedProps.capabilities).toEqual(expect.arrayContaining(['ask.range', 'review', 'set.consent']))
  })
})

describe('card kit: questions', () => {
  it('options with details answer in one tap', async () => {
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'Which loan?', allow_text: false,
      options: [{ id: 'auto', label: 'Car loan', description: 'from 16.9%' }, { id: 'cash', label: 'Cash' }] })))
    expect($(el, '.opt .muted').textContent).toBe('from 16.9%')
    $$(el, '.opt')[0].click()
    await tick(5)
    expect(resume()).toEqual({ answer: { ids: ['auto'] } })
  })

  it('a comparison marks the recommended option and notes document numbers', async () => {
    const opts = [3, 5, 7].map((y) => ({ id: String(y), label: `${y} years`, attrs: { Monthly: `${y}0 000`, Overpay: `${y}00 000` } }))
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'Term?', options: opts, recommended: '5', sources: [{ title: 'Tariffs' }], allow_text: false })))
    expect($$(el, '.cmp .opt')).toHaveLength(3)
    expect($(el, '.cmp-col.rec').textContent).toContain('Recommended')
    expect($(el, '.note').textContent).toBe('From the documents')
  })

  it('a long list searches, suggested first', async () => {
    const opts = Array.from({ length: 40 }, (_, i) => ({ id: `b${i}`, label: `Bank ${i}` }))
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'Bank?', options: opts, suggested: ['b7', 'b9'], allow_text: false })))
    expect($$(el, '.opts .opt').map((b) => b.querySelector('b')!.textContent)).toEqual(['Bank 7', 'Bank 9'])
    const box = $(el, '.search') as HTMLInputElement
    box.value = 'bank 3'; box.dispatchEvent(new Event('input'))
    expect($$(el, '.opts .opt').map((b) => b.querySelector('b')!.textContent)).toEqual(['Bank 3', 'Bank 30', 'Bank 31', 'Bank 32', 'Bank 33', 'Bank 34', 'Bank 35', 'Bank 36', 'Bank 37', 'Bank 38', 'Bank 39'])
  })

  it('a date question offers days, and the tap fills the field', async () => {
    const { el, applyChanges } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'When?', field: 'call_date', label: 'Call date',
      applies: true, input: { type: 'date' }, allow_text: true })))
    const days = $$(el, '.strip .chip')
    expect(days[0].textContent).toBe('Today')
    expect(days[1].textContent).toBe('Tomorrow')
    days[1].click()
    await tick(5)
    expect(Object.keys(applyChanges.mock.calls[0][0])).toEqual(['call_date'])
    expect(resume()).toMatchObject({ answer: { text: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) }, config: expect.anything() })
  })

  it('time slots come from the host', async () => {
    const getSlots = vi.fn(async () => ['10:00', '14:30'])
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'What time?', field: 'call_time', input: { type: 'time' }, allow_text: true })), { getSlots })
    await tick(5)
    expect($$(el, '.slots .chip').map((b) => b.textContent)).toEqual(['10:00', '14:30'])
    $$(el, '.slots .chip')[1].click()
    await tick(5)
    expect(resume()).toEqual({ answer: { text: '14:30' } })   // not applies: only answers
  })

  it('a small range is a stepper with a live preview, and Set fills the field', async () => {
    const preview = vi.fn((_f: string, v: number) => `${v * 10} per month`)
    const { el, applyChanges, onDirective } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'Term?', field: 'term', label: 'Term',
      applies: true, previous: 5, input: { type: 'number', min: 1, max: 7, step: 1, unit: 'years' }, allow_text: true, reveal: [] })), { preview })
    await tick(5)
    expect($(el, '.range-p').textContent).toBe('50 per month')
    ;($(el, '.stepper .btn') as HTMLButtonElement).click()   // minus
    await tick(5)
    expect($(el, '.range-p').textContent).toBe('40 per month')
    const set = $(el, '.range .btn.pri') as HTMLButtonElement
    expect(set.textContent).toBe('Set 4 years')
    set.click()
    await tick(5)
    expect(applyChanges).toHaveBeenCalledWith({ term: 4 })
    expect($(el, '.card .ok-line .btn').textContent).toBe('Undo')
    expect(onDirective).toHaveBeenCalledWith(expect.objectContaining({ target: 'term' }))
  })

  it('several short fields in one card', async () => {
    const { el, applyChanges } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'Your name', allow_text: true,
      fields: [{ name: 'first_name', label: 'First name' }, { name: 'last_name', label: 'Last name' }] })))
    const [a, b] = $$(el, '.fields .text-in') as HTMLInputElement[]
    const btn = $(el, '.fields .btn.pri') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
    a.value = 'Anna'; a.dispatchEvent(new Event('input'))
    b.value = 'Petrova'; b.dispatchEvent(new Event('input'))
    expect(btn.textContent).toBe('Fill in 2 fields')
    btn.click()
    await tick(5)
    expect(applyChanges).toHaveBeenCalledWith({ first_name: 'Anna', last_name: 'Petrova' })
    expect(resume()).toMatchObject({ answers: { first_name: 'Anna', last_name: 'Petrova' } })
  })
})

describe('card kit: field card, review, confirm', () => {
  it('consents start unticked and the button says what is missing', async () => {
    const { el, applyChanges } = await chatWith(run(interrupt({ type: 'set_fields', card_id: 'c', changes: [
      { name: 'c_credit', label: 'Credit check', kind: 'bool', value: true, display: 'yes', consent: true, required: true, doc: { text: 'We check your history.' } },
      { name: 'c_sms', label: 'Offers by SMS', kind: 'bool', value: true, display: 'yes', consent: true, required: false },
    ] })))
    const btn = $(el, '.card .btn.pri') as HTMLButtonElement
    expect(btn.textContent).toBe('Tick the required: 1 left')
    expect(btn.disabled).toBe(true)
    const read = $$(el, '.card .btn.link').find((b) => b.textContent === 'Read')!
    read.click()
    expect($(el, '.doc').hidden).toBe(false)
    ;($$(el, '.card input[type=checkbox]')[0] as HTMLInputElement).click()
    expect(btn.textContent).toBe('Agree')
    btn.click()
    await tick(5)
    expect(applyChanges).toHaveBeenCalledWith({ c_credit: true })
  })

  it('a shared reason is said once; issues and document checks show in rows', async () => {
    const { el } = await chatWith(run(interrupt({ type: 'set_fields', card_id: 'c', source: { kind: 'document', title: 'Passport', found: 2 }, changes: [
      { name: 'p_no', label: 'Passport number', kind: 'text', value: '4512123456', display: '4512123456', reason: 'From the photo' },
      { name: 'p_by', label: 'Issued by', kind: 'text', value: 'MVD', display: 'MVD', reason: 'From the photo', confidence: 'low',
        issue: { severity: 'warning', message: 'Looks short', why: 'Usually longer' } },
    ] })))
    expect($(el, '.doc-head').textContent).toContain('Passport')
    expect($(el, '.doc-head').textContent).toContain('to check: 1')
    expect($$(el, '.shared').map((x) => x.textContent)).toEqual(['From the photo'])
    expect($(el, '.card').textContent).toContain('4512123456')
    expect($(el, '.tag.warn').textContent).toBe('check')
    expect($(el, '.issue-line').textContent).toContain('Looks short')
  })

  it('the review blocks sending until errors are fixed, with Undo', async () => {
    const { el, applyChanges, onDirective } = await chatWith(run(interrupt({ type: 'review', card_id: 'r', mode: 'submit', issues: [
      { severity: 'error', field: 'phone', label: 'Phone', message: 'needs 10 digits', fix: { value: '0965899964', display: '0965899964' }, reveal: [] },
      { severity: 'warning', field: 'car_year', label: 'Car', message: 'is 9 years old at the end', detail: 'The limit is 10 years', source: { title: 'Rules' } },
    ] })), {}, { phone: '+380965899964' })
    const main = $(el, '.rev .btn.pri') as HTMLButtonElement
    expect(main.textContent).toBe('Fix 1 to send')
    main.click()
    expect(onDirective).toHaveBeenCalledWith(expect.objectContaining({ target: 'phone' }))
    $$(el, '.rev .btn.link').find((b) => b.textContent === 'Fix')!.click()
    await tick(5)
    expect(applyChanges).toHaveBeenCalledWith({ phone: '0965899964' })
    expect($(el, '.row.issue.fixed .btn').textContent).toBe('Undo')
    expect(main.textContent).toBe('Send')
    main.click()
    await tick(5)
    expect(resume()).toMatchObject({ action: 'fixed', names: ['phone'], config: expect.anything() })
  })

  it('the status review continues with the next section', async () => {
    const { el } = await chatWith(run(interrupt({ type: 'review', card_id: 'r', mode: 'status', sections: [
      { name: 'applicant', label: 'Applicant', left: 0 }, { name: 'car', label: 'Car', left: 2, reveal: [] }] })))
    expect($(el, '.rev .card-q').textContent).toBe('Fields left: 2')
    const btn = $(el, '.rev .btn.pri') as HTMLButtonElement
    expect(btn.textContent).toBe('Continue with Car')
    btn.click()
    await tick(5)
    expect(resume()).toEqual({ action: 'continue', section: 'car' })
  })

  it('a confirm shows details, becomes a receipt, and asks for a rating once', async () => {
    mockRuns(run(interrupt({ type: 'confirm', card_id: 'k', title: 'Send the application?', details: [{ label: 'Amount', value: '1 500 000' }],
      consequence: 'The bank checks your credit history.' })),
    run({ type: 'CUSTOM', name: 'receipt', value: { card_id: 'k', number: '48-1192', eta: 'Answer within 1 day' } }, ...text('m2', 'Sent.')))
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off', lang: 'en', url: '/agent/run' })) el.setAttribute(k, v)
    document.body.appendChild(el)
    await tick()
    el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
    await el.send('go')
    await tick(5)
    expect($(el, '.details').textContent).toContain('Amount')
    expect($(el, '.consequence').textContent).toContain('credit history')
    ;($(el, '.card .btn.pri') as HTMLButtonElement).click()
    await tick(10)
    expect($(el, '.receipt').textContent).toContain('48-1192')
    expect($(el, '.receipt .btn').textContent).toBe('Copy number')
    $$(el, '.feedback .thumb')[0].click()
    await tick(5)
    expect(fetches.find((f) => f.url.endsWith('/feedback'))?.body).toMatchObject({ value: 1, card_id: 'k' })
    expect($(el, '.feedback').textContent).toBe('Thanks for the feedback')
  })

  it('sources become chips under the answer', async () => {
    const { el } = await chatWith(run(...text('m1', 'Early repayment is free.'),
      { type: 'CUSTOM', name: 'sources', value: { items: [{ title: 'Tariffs 2026', section: 'Early repayment', quote: 'free after 3 months' }] } } as AguiEvent))
    const chip = $(el, '.srcs .src-chip')
    expect(chip.textContent).toBe('Tariffs 2026 › Early repayment')
    chip.click()
    expect($(el, '.quote').textContent).toContain('free after 3 months')
  })
})

describe('Apple-style controls', () => {
  it('a number field has its own stepper on the right edge', async () => {
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'How much?', allow_text: true,
      fields: [{ name: 'amount', label: 'Amount', input: { type: 'number' } }, { name: 'extra', label: 'Extra', input: { type: 'number' } }] })))
    const boxes = $$(el, '.fields .num')
    expect(boxes).toHaveLength(2)
    const input = boxes[0].querySelector('input') as HTMLInputElement
    const [up, down] = [...boxes[0].querySelectorAll('.num-b')] as HTMLButtonElement[]
    up.click(); up.click(); down.click()
    expect(input.value).toBe('1')
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }))
    expect(input.value).toBe('2')
    expect(($(el, '.fields .btn.pri') as HTMLButtonElement).textContent).toBe('Required fields left: 1')
  })
})

describe('our own date and time pickers', () => {
  it('a past date opens the calendar on the right month; a tap answers', async () => {
    const { el, applyChanges } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'When was the company founded?', field: 'founded',
      applies: true, input: { type: 'date', max: '2020-03-15' }, allow_text: true })))
    expect($(el, '.cal-title').textContent).toContain('March 2020')
    expect($$(el, '.strip .chip')).toHaveLength(0)                       // no quick days for the past
    expect(($(el, 'input[type=date]') as HTMLInputElement).hidden).toBe(true)   // no browser picker
    const later = $$(el, '.cal-d').find((b) => b.textContent === '20') as HTMLButtonElement
    expect(later.disabled).toBe(true)                                     // after max
    ;($$(el, '.cal-d').find((b) => b.textContent === '10') as HTMLButtonElement).click()
    await tick(5)
    expect(applyChanges).toHaveBeenCalledWith({ founded: '2020-03-10' })
  })

  it('the title switches to years, then months', async () => {
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'Born?', input: { type: 'date', max: '2008-01-01' }, allow_text: true })))
    ;($(el, '.cal-title') as HTMLButtonElement).click()
    expect($(el, '.cal-title').textContent).toBe('2004 – 2015')
    ;($$(el, '.cal-nav')[0] as HTMLButtonElement).click()                 // the previous 12 years
    ;($$(el, '.cal-y').find((b) => b.textContent === '1999') as HTMLButtonElement).click()
    ;($$(el, '.cal-y')[4] as HTMLButtonElement).click()                  // May
    expect($(el, '.cal-title').textContent).toContain('May 1999')
  })

  it('a date among several fields uses the calendar field', async () => {
    const { el, applyChanges } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'Children', allow_text: true,
      fields: [{ name: 'c1', label: 'Child #1 date of birth', input: { type: 'date', max: '2026-01-01' } }] })))
    const face = $(el, '.date-face') as HTMLButtonElement
    expect(face.textContent).toContain('Choose a date')
    face.click()
    ;($$(el, '.cal-d').find((b) => !(b as HTMLButtonElement).disabled) as HTMLButtonElement).click()
    expect(face.textContent).not.toContain('Choose a date')
    ;($(el, '.fields .btn.pri') as HTMLButtonElement).click()
    await tick(5)
    expect(Object.keys(applyChanges.mock.calls[0][0])).toEqual(['c1'])
  })

  it('a time without slots shows a time grid, not the browser picker', async () => {
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'What time?', input: { type: 'time', min: '10:00', max: '12:00' }, allow_text: true })))
    expect($$(el, '.times .chip').map((b) => b.textContent)).toEqual(['10:00', '10:30', '11:00', '11:30', '12:00'])
    $$(el, '.times .chip')[2].click()
    await tick(5)
    expect(resume()).toEqual({ answer: { text: '11:00' } })
  })

  it('number options carry no number-key hints', async () => {
    const { el } = await chatWith(run(interrupt({ type: 'ask', card_id: 'q', question: 'How many?', allow_text: false,
      options: [{ id: '0', label: 'None' }, { id: '1', label: '1' }, { id: '2', label: '2' }] })))
    expect($$(el, '.chip kbd')).toHaveLength(0)
  })
})

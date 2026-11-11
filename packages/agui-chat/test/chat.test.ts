import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import { parseBlock, sseEvents } from '../src/transport'
import { newState, step, visible } from '../src/typewriter'
import type { AguiEvent } from '../src/types'

// ---------------------------------------------------------------- helpers

function sse(events: AguiEvent[]): Response {
  const text = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
  const bytes = new TextEncoder().encode(text)
  const body = new ReadableStream<Uint8Array>({
    start(c) { c.enqueue(bytes.slice(0, 17)); c.enqueue(bytes.slice(17)); c.close() },   // split mid-event
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

const run = (...body: AguiEvent[]): AguiEvent[] => [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, ...body, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]
const text = (id: string, s: string): AguiEvent[] => [
  { type: 'TEXT_MESSAGE_START', messageId: id, role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: id, delta: s },
  { type: 'TEXT_MESSAGE_END', messageId: id }]
const interrupt = (v: unknown): AguiEvent => ({ type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify(v) })

let bodies: any[] // eslint-disable-line @typescript-eslint/no-explicit-any
function mockRuns(...runs: AguiEvent[][]): void {
  bodies = []
  const queue = [...runs]
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => {
    bodies.push(JSON.parse(String(init?.body)))
    return sse(queue.shift() ?? run())
  }))
}

async function mount(attrs: Record<string, string> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat')
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off', ...attrs })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  return el
}

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const $ = (el: AguiChatElement, sel: string) => el.shadowRoot!.querySelector(sel) as HTMLElement
const $$ = (el: AguiChatElement, sel: string) => [...el.shadowRoot!.querySelectorAll(sel)] as HTMLElement[]

beforeEach(() => { document.body.innerHTML = ''; vi.spyOn(console, 'warn').mockImplementation(() => {}) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

// ---------------------------------------------------------------- transport

describe('transport', () => {
  it('parses SSE blocks split across chunks', async () => {
    const res = sse(run(...text('m1', 'Hi')))
    const got: string[] = []
    for await (const e of sseEvents(res.body!)) got.push(e.type)
    expect(got).toEqual(['RUN_STARTED', 'TEXT_MESSAGE_START', 'TEXT_MESSAGE_CONTENT', 'TEXT_MESSAGE_END', 'RUN_FINISHED'])
    expect(parseBlock(': comment')).toBeNull()
    expect(parseBlock('event: x\ndata: {"type":"A"}')).toEqual({ type: 'A' })
  })
})

// ---------------------------------------------------------------- typewriter

describe('typewriter', () => {
  it('reveals at least the base speed and faster with a backlog', () => {
    const slow = newState(), fast = newState()
    const short = 'a'.repeat(30), long = 'a'.repeat(3000)
    for (let t = 16; t <= 1000; t += 16) { step(slow, short, t); step(fast, long, t) }
    expect(slow.shown).toBe(30)
    expect(fast.shown).toBeGreaterThan(1000)   // three times the backlog per second
  })

  it('finishes short words, never splits an emoji, closes bold', () => {
    const st = newState()
    step(st, 'Hello wonderful world', 100)
    step(st, 'Hello wonderful world', 116)
    expect(['Hello', 'Hello wonderful', 'Hello wonderful world']).toContain('Hello wonderful world'.slice(0, st.shown))
    const em = newState(0)
    em.acc = 0.99
    step(em, '😀 ok', 16)
    expect(em.shown).not.toBe(1)
    expect(visible('a **bo', 6)).toBe('a **bo**')
  })
})

// ---------------------------------------------------------------- the element

describe('<agui-chat>', () => {
  it('sends a RunAgentInput and streams the answer', async () => {
    mockRuns(run(...text('m1', 'Hello **there**')))
    const el = await mount()
    await el.send('hi')
    const b = bodies[0]
    expect(b.threadId).toBe(el.threadId)
    expect(b.messages.at(-1)).toMatchObject({ role: 'user', content: 'hi' })
    expect(b.tools).toEqual([])
    expect($(el, '.msg.ai').innerHTML).toContain('<b>there</b>')
    expect($$(el, '.msg.me')).toHaveLength(1)
  })

  it('shows tool steps with sub-steps, and hides them when off', async () => {
    mockRuns(run(
      { type: 'TOOL_CALL_START', toolCallId: 'c1', toolCallName: 'ask_documents' },
      { type: 'TOOL_CALL_ARGS', toolCallId: 'c1', delta: '{}' }, { type: 'TOOL_CALL_END', toolCallId: 'c1' },
      { type: 'CUSTOM', name: 'tool_progress', value: { parent_id: 'c1', name: 'docs.search' } },
      { type: 'TOOL_CALL_RESULT', toolCallId: 'c1', messageId: 'c1-r', content: 'found' },
      ...text('m1', 'Done.')))
    const el = await mount()
    el.use(formguide({ getState: () => ({ config: {}, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
    await el.send('rate?')
    const steps = $(el, '.steps')
    expect(steps.textContent).toContain('Searching the business documents')
    expect(steps.textContent).toContain('Steps: 1')
    expect($$(el, '.steps li.ok').length).toBe(2)
    expect(steps.classList.contains('collapsed')).toBe(true)
    el.setAttribute('tool-steps', 'off')
    expect(steps.hidden).toBe(true)
  })

  it('renders an interrupt with a registered renderer and resumes with its value', async () => {
    mockRuns(run(interrupt({ type: 'pick_seat', card_id: 'k1', seats: ['1A', '2B'] })), run(...text('m2', 'Seat 2B.')))
    const el = await mount()
    el.renderers.set('pick_seat', (it, c) => {
      const b = document.createElement('button')
      b.className = 'seat'
      b.textContent = it.seats[1]
      b.onclick = () => c.resolve({ seat: it.seats[1] })
      return b
    })
    await el.send('book')
    ;($(el, '.seat') as HTMLButtonElement).click()
    await tick(5)
    expect(bodies[1].forwardedProps.command.resume).toEqual({ seat: '2B' })
    el.setAttribute('resume-style', 'resume')
    mockRuns(run(interrupt({ type: 'pick_seat', card_id: 'k2', seats: ['1A', '2B'] })), run())
    await el.send('again')
    ;($$(el, '.seat').at(-1) as HTMLButtonElement).click()
    await tick(5)
    expect(bodies[1].resume).toEqual([{ interrupt_id: 'k2', status: 'resolved', payload: { seat: '2B' } }])
  })

  it('shows a fallback card for an unknown interrupt type', async () => {
    mockRuns(run(interrupt({ type: 'mystery', card_id: 'x', a: 1 })), run())
    const el = await mount()
    await el.send('?')
    expect($(el, '.card').textContent).toContain('mystery')
    ;($(el, '.card .btn') as HTMLButtonElement).click()
    await tick(5)
    expect(bodies[1].forwardedProps.command.resume).toEqual({ accepted: false })
  })

  it('runs frontend tools and continues with their results', async () => {
    mockRuns(run(
      { type: 'TOOL_CALL_START', toolCallId: 'f1', toolCallName: 'get_locale' },
      { type: 'TOOL_CALL_ARGS', toolCallId: 'f1', delta: '{"x":1}' }, { type: 'TOOL_CALL_END', toolCallId: 'f1' }),
    run(...text('m2', 'You are in Lyon.')))
    const el = await mount()
    const handler = vi.fn(() => 'fr-FR')
    el.registerTool({ name: 'get_locale', description: 'locale', handler })
    await el.send('where am I?')
    await tick(5)
    expect(handler).toHaveBeenCalledWith({ x: 1 }, expect.anything())
    expect(bodies[0].tools[0].name).toBe('get_locale')
    expect(bodies[1].messages.at(-1)).toMatchObject({ role: 'tool', toolCallId: 'f1', content: 'fr-FR' })
    expect($$(el, '.steps')).toHaveLength(0)            // unlabelled frontend tools are not steps
  })

  it('shows quick replies and starters, and applies options live', async () => {
    mockRuns(run(...text('m1', 'Ok.'), { type: 'CUSTOM', name: 'suggestions', value: { items: ['What next?', 'Thanks'] } }))
    const el = await mount()
    el.options = { starters: ['Where do I start?'], title: 'Help' }
    expect($(el, '.empty').textContent).toContain('Where do I start?')
    expect($(el, '.title').textContent).toBe('Help')
    el.options = { nonsense: 1 } as never
    expect(console.warn).toHaveBeenCalled()
    await el.send('hi')
    expect($$(el, '.quick .chip').map((c) => c.textContent)).toEqual(['What next?', 'Thanks'])
    el.setAttribute('quick-replies', 'off')
    expect($(el, '.quick').hidden).toBe(true)
    el.setAttribute('mic', 'off')
    expect($(el, '.mic').hidden).toBe(true)
  })

  it('takes a thread id from options and switches to it', async () => {
    mockRuns(run())
    const el = await mount()
    const seen: string[] = []
    el.addEventListener('agui:thread', (e) => seen.push((e as CustomEvent).detail))
    el.options = { threadId: 'thread-b' }
    expect(el.threadId).toBe('thread-b')
    expect(seen).toEqual(['thread-b'])
    expect(console.warn).not.toHaveBeenCalled()
  })

  it('shakes on an empty send and shows a retry after an error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{"detail":"boom"}', { status: 500 })))
    const el = await mount()
    ;($(el, '.send') as HTMLButtonElement).disabled = false
    $(el, '.send').click()
    expect($(el, '.foot').classList.contains('nudge')).toBe(true)
    await el.send('hi')
    expect($(el, '.error').textContent).toContain('boom')
  })
})

// ---------------------------------------------------------------- dictation and attachments

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

describe('dictation and attachments', () => {
  it('clears the composer for good when a dictated message is sent', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition)
    mockRuns(run(...text('m1', 'The Loan tab is next.')))
    const el = await mount({ 'mic-lang': 'ru-RU' })
    $(el, '.mic').click()
    const rec = FakeRecognition.last!
    expect(rec.lang).toBe('ru-RU')
    rec.say('okay which field is next', false)
    const input = $(el, 'textarea') as HTMLTextAreaElement
    expect(input.value).toBe('okay which field is next')
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    expect(rec.aborted).toBe(true)
    rec.say('okay which field is next')         // a late final result after sending
    await tick(5)
    expect(input.value).toBe('')
    expect($(el, '.mic').classList.contains('on')).toBe(false)
    expect(bodies[0].messages.at(-1).content).toBe('okay which field is next')
  })

  it('sends when dictation stops with mic-auto-send', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition)
    mockRuns(run(...text('m1', 'Ok.')))
    const el = await mount({ 'mic-auto-send': '' })
    $(el, '.mic').click()
    FakeRecognition.last!.say('book a haircut')
    $(el, '.mic').click()                         // stop: the result is final, the message goes
    await tick(20)
    expect(bodies[0].messages.at(-1).content).toBe('book a haircut')
  })

  it('takes attachment settings from options', async () => {
    mockRuns(run(...text('m1', 'Got it.')))
    const el = await mount({ 'attach-accept': '.pdf', 'attach-max-mb': '1' })
    expect($(el, '.clip').hidden).toBe(true)                    // nobody can upload yet
    const upload = vi.fn(async (f: File) => ({ id: `att_${f.name}`, filename: f.name }))
    el.options = { upload, attachMultiple: false }
    expect($(el, '.clip').hidden).toBe(false)
    const picker = $(el, 'input[type=file]') as HTMLInputElement
    expect(picker.accept).toBe('.pdf')
    expect(picker.multiple).toBe(false)
    const small = new File(['x'], 'a.pdf'), big = new File([new Uint8Array(2 * 1024 * 1024)], 'b.pdf')
    Object.defineProperty(picker, 'files', { value: [big, small], configurable: true })
    picker.dispatchEvent(new Event('change'))
    await tick(5)
    expect(upload).toHaveBeenCalledTimes(0)                      // multiple off: only the first, and it is too big
    expect($(el, '.hint').textContent).toContain('b.pdf')
    Object.defineProperty(picker, 'files', { value: [small], configurable: true })
    picker.dispatchEvent(new Event('change'))
    await tick(5)
    expect(upload).toHaveBeenCalledTimes(1)
    expect($$(el, '.files .chip').map((c) => c.textContent)).toEqual([expect.stringContaining('a.pdf')])
    el.setAttribute('attach', 'off')
    expect($(el, '.clip').hidden).toBe(true)
  })
})

// ---------------------------------------------------------------- formguide cards

describe('formguide plugin', () => {
  const CHANGES = [
    { name: 'first_name', label: 'First name', value: 'Anna', display: 'Anna', previous: 'Ana', previous_display: 'Ana', reveal: [] },
    { name: 'loan_amount', label: 'Amount', value: 1500000, display: '1500000', previous: null, previous_display: null, reveal: [] },
    { name: 'gender', label: 'Gender', value: { id: 'f', name: 'Female' }, display: 'Female', previous: null, previous_display: null },
  ]

  async function withPlugin(first: AguiEvent[], opts: Record<string, unknown> = {}) {
    mockRuns(first, run(...text('m2', 'Done.')))
    const el = await mount()
    const applyChanges = vi.fn(async (c: Record<string, unknown>) => ({ state: c }))
    const state = { config: { props: { gender: { options: [{ id: 'm', name: 'Male' }, { id: 'f', name: 'Female' }] } }, state: {} }, jsx_hash: 'h', form_id: 'loan', ui: { focused: null } }
    el.use(formguide({ getState: () => state, applyChanges, ...opts }))
    await el.send('go')
    await tick()
    return { el, applyChanges, state }
  }

  it('sends the form as state and applies kept, edited rows', async () => {
    const { el, applyChanges } = await withPlugin(run(interrupt({ type: 'set_fields', card_id: 'c1', changes: CHANGES })))
    expect(bodies[0].state.jsx_hash).toBe('h')
    expect($(el, '.card').textContent).toContain('Ana')                           // old -> new
    const checks = $$(el, '.card input[type=checkbox]') as HTMLInputElement[]
    checks[2].click()                                                                 // untick gender
    const edit = $$(el, '.card .btn.link').find((b) => b.textContent === 'Edit' && b.closest('.row')!.textContent!.includes('Amount'))!
    edit.click()
    const input = $(el, '.card .field input') as HTMLInputElement
    input.value = '1200000'
    ;($(el, '.card .field .btn') as HTMLButtonElement).click()
    const fill = $$(el, '.card .btn.pri')[0] as HTMLButtonElement
    expect(fill.textContent).toBe('Fill in 2 of 3')
    fill.click()
    await tick(5)
    expect(applyChanges).toHaveBeenCalledWith({ first_name: 'Anna', loan_amount: 1200000 })
    const resume = bodies[1].forwardedProps.command.resume
    expect(resume).toMatchObject({ accepted: true, names: ['first_name', 'loan_amount'], edited: { loan_amount: 1200000 } })
    expect($(el, '.card .ok-line').textContent).toContain('Partly filled in')
    expect($(el, '.card .ok-line .btn').textContent).toBe('Undo')
  })

  it('turns card features off with options', async () => {
    mockRuns(run(interrupt({ type: 'set_fields', card_id: 'c1', changes: CHANGES })))
    const el = await mount()
    el.options = { cards: { set_fields: { select: false, edit: false, diff: false, jump: false } } }
    el.use(formguide({ getState: () => ({ config: {}, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
    await el.send('go')
    expect($$(el, '.card input[type=checkbox]')).toHaveLength(0)
    expect($$(el, '.card .btn.link')).toHaveLength(0)
    expect($(el, '.card').textContent).not.toContain('Ana')
  })

  it('answers a question by click, number key and typed text', async () => {
    const q = { type: 'ask', card_id: 'q1', question: 'Which loan?', options: [{ id: 'auto', label: 'Car loan' }, { id: 'cash', label: 'Cash' }], multiple: false, allow_text: true }
    let { el } = await withPlugin(run(interrupt(q)))
    $(el, '.card').dispatchEvent(new KeyboardEvent('keydown', { key: '2', bubbles: true }))
    await tick(5)
    expect(bodies[1].forwardedProps.command.resume).toEqual({ answer: { ids: ['cash'] } })

    ;({ el } = await withPlugin(run(interrupt({ ...q, card_id: 'q2', options: [], input: { type: 'date', min: '2026-11-12' } }))))
    const inp = $(el, '.card .text-in') as HTMLInputElement
    expect(inp.type).toBe('date')
    inp.value = '2026-11-20'
    inp.dispatchEvent(new Event('input'))
    ;($(el, '.card .btn.pri') as HTMLButtonElement).click()
    await tick(5)
    expect(bodies[1].forwardedProps.command.resume).toEqual({ answer: { text: '2026-11-20' } })
  })

  it('confirms and skips', async () => {
    const { el } = await withPlugin(run(interrupt({ type: 'confirm', card_id: 'k', title: 'Submit?', message: 'Sure?', danger: true })))
    expect($(el, '.card .btn.danger').textContent).toBe('Confirm')
    ;($(el, '.card .btn.sec') as HTMLButtonElement).click()
    await tick(5)
    expect(bodies[1].forwardedProps.command.resume).toEqual({ accepted: false })
  })

  it('uploads a requested file and resumes with its id', async () => {
    class FakeXHR {
      upload = { onprogress: null as null | ((e: unknown) => void) }
      status = 200; statusText = 'OK'; responseText = '{"id":"att_12345678","filename":"passport.pdf"}'
      onload: null | (() => void) = null; onerror: null | (() => void) = null
      url = ''
      open(_m: string, u: string) { this.url = u }
      send() { setTimeout(() => { this.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 1 }); this.onload?.() }) }
    }
    vi.stubGlobal('XMLHttpRequest', FakeXHR)
    const { el } = await withPlugin(run(interrupt({ type: 'upload', card_id: 'u', prompt: 'Upload your passport', accept: '.pdf', multiple: false })))
    const zone = $(el, '.card [role=button]')
    const file = new File(['%PDF'], 'passport.pdf', { type: 'application/pdf' })
    const drop = new Event('drop', { bubbles: true }) as Event & { dataTransfer: unknown }
    Object.defineProperty(drop, 'dataTransfer', { value: { files: [file] } })
    zone.dispatchEvent(drop)
    await tick(20)
    expect(bodies[1].forwardedProps.command.resume).toEqual({ attachment_ids: ['att_12345678'] })
    expect($(el, '.card .ok-line').textContent).toContain('passport.pdf')
  })

  it('shows no separate step for the tool that made the card', async () => {
    const { el } = await withPlugin(run(
      { type: 'TOOL_CALL_START', toolCallId: 'q', toolCallName: 'ask_user' }, { type: 'TOOL_CALL_END', toolCallId: 'q' },
      interrupt({ type: 'ask', card_id: 'q1', question: 'Which?', options: [{ id: 'a', label: 'A' }], multiple: false, allow_text: false })))
    expect($$(el, '.steps')).toHaveLength(0)
    ;($(el, '.card .chip') as HTMLButtonElement).click()
    await tick(5)
    expect($$(el, '.card .chip')).toHaveLength(0)                // the answered card shrinks
    expect($(el, '.card .ok-line').textContent).toContain('A')
  })

  it('passes directives to the host', async () => {
    const onDirective = vi.fn()
    await withPlugin(run({ type: 'CUSTOM', name: 'ui_directive', value: { type: 'focus', target: 'email', reveal: [], hint: 'Here' } }, ...text('m1', 'There.')), { onDirective })
    expect(onDirective).toHaveBeenCalledWith({ type: 'focus', target: 'email', reveal: [], hint: 'Here' })
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
type Obs = { next: (e: unknown) => void; complete: () => void }

/** An agent whose turns finish when the test says so: release() ends the oldest open turn. */
function agent() {
  const runs: { input: Record<string, unknown>; done: () => void; aborted: boolean }[] = []
  return {
    runs,
    release: async () => { runs.find((r) => !r.aborted && (r as { over?: boolean }).over !== true)!.done(); await tick(20) },
    run: (input: Record<string, unknown>) => ({ subscribe: (o: Obs) => {
      const n = runs.length + 1
      const r = { input, aborted: false, over: false, done: () => {
        r.over = true
        for (const e of [{ type: 'TEXT_MESSAGE_START', messageId: `a${n}`, role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: `a${n}`, delta: `Answer ${n}` },
          { type: 'TEXT_MESSAGE_END', messageId: `a${n}` }, { type: 'RUN_FINISHED', threadId: 't', runId: `r${n}` }]) o.next(e)
        o.complete()
      } }
      runs.push(r)
      setTimeout(() => o.next({ type: 'RUN_STARTED', threadId: 't', runId: `r${n}` }))
      return { unsubscribe() { r.aborted = true } }
    } }),
  }
}

async function mount(): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off', 'thread-id': 'q-test' })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  return el
}
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]
const lastUser = (input: Record<string, unknown>) => (input.messages as { role: string; content: string }[]).filter((m) => m.role === 'user').at(-1)!.content

beforeEach(() => { document.body.innerHTML = ''; localStorage.clear(); vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('the message queue', () => {
  it('a message sent while it answers waits last in the log, then goes by itself; the answer lands above it', async () => {
    const el = await mount(), a = agent()
    el.agent = a as never
    void el.send('first')
    await tick(5)
    await el.send('second')                                             // the assistant is still answering
    expect(a.runs).toHaveLength(1)
    const q = $$(el, '.msg.queued')
    expect(q).toHaveLength(1)
    expect(q[0].querySelector('.q-now')!.textContent).toBe('Send now')
    expect((el.shadowRoot!.querySelector('textarea') as HTMLTextAreaElement).placeholder).toBe('↵ to queue')
    expect(el.shadowRoot!.querySelector('.log')!.lastElementChild!.classList.contains('queued')).toBe(true)   // the dots above it
    await a.release()
    await tick(300)                                                      // its line eases away
    const log = [...el.shadowRoot!.querySelector('.log')!.children].filter((c) => c.classList.contains('msg')).map((c) => c.textContent)
    expect(log.slice(0, 3).map((t) => t!.slice(0, 8))).toEqual(['first', 'Answer 1', 'second'])  // the answer above the queued one
    expect(a.runs).toHaveLength(2)                                       // it went by itself
    expect(lastUser(a.runs[1].input)).toBe('second')
    expect($$(el, '.msg.queued')).toHaveLength(0)
  })

  it('several wait in order; Send now stops the answer and sends that one; Remove takes one out', async () => {
    const el = await mount(), a = agent()
    el.agent = a as never
    void el.send('first')
    await tick(5)
    await el.send('two'); await el.send('three'); await el.send('four')
    expect($$(el, '.msg.queued').map((m) => m.querySelector('.bubble')!.textContent)).toEqual(['two', 'three', 'four'])
    ;($$(el, '.msg.queued')[2].querySelector('.q-x') as HTMLButtonElement).click()
    expect($$(el, '.msg.queued')).toHaveLength(2)
    ;($$(el, '.msg.queued')[1].querySelector('.q-now') as HTMLButtonElement).click()   // "three", now
    await tick(20)
    expect(a.runs[0].aborted).toBe(true)
    expect(lastUser(a.runs[1].input)).toBe('three')
    expect($$(el, '.msg.queued').map((m) => m.querySelector('.bubble')!.textContent)).toEqual(['two'])
  })

  it('Edit puts the text back into the field and out of the queue', async () => {
    const el = await mount(), a = agent()
    el.agent = a as never
    void el.send('first')
    await tick(5)
    await el.send('typo here')
    ;($$(el, '.msg.queued')[0].querySelector('.q-edit') as HTMLButtonElement).click()
    expect((el.shadowRoot!.querySelector('textarea') as HTMLTextAreaElement).value).toBe('typo here')
    expect($$(el, '.msg.queued')).toHaveLength(0)
  })

  it('a failed answer pauses the queue: the error above it, Try again goes on', async () => {
    const el = await mount()
    const runs: string[] = []
    let fail = (): void => {}, finish = (): void => {}
    el.agent = { run: (input: Record<string, unknown>) => ({ subscribe: (o: Obs) => {
      runs.push(lastUser(input))
      fail = () => { o.next({ type: 'RUN_ERROR', message: 'boom' }); o.complete() }
      finish = () => { o.next({ type: 'RUN_FINISHED', threadId: 't', runId: 'r' }); o.complete() }
      setTimeout(() => o.next({ type: 'RUN_STARTED', threadId: 't', runId: 'r' }))
      return { unsubscribe() {} }
    } }) } as never
    void el.send('first')
    await tick(5)
    await el.send('second')
    fail(); await tick(30)
    expect([...el.shadowRoot!.querySelector('.log')!.children].map((c) => c.className)).toEqual(['msg me', 'error', 'msg me queued'])
    expect(runs).toEqual(['first'])                                      // nothing more fails in a row
    ;(el.shadowRoot!.querySelector('.error .btn') as HTMLButtonElement).click()   // Try again
    await tick(10); finish(); await tick(30)
    expect(runs).toEqual(['first', 'first', 'second'])
  })

  it('Stop pauses the queue and says so; a new message goes in behind it, and they go in order', async () => {
    const el = await mount(), a = agent()
    el.agent = a as never
    void el.send('first')
    await tick(5)
    await el.send('two')
    el.stop()
    await tick(20)
    expect($$(el, '.msg.queued .q-tag')[0].textContent).toBe('Paused')
    expect(a.runs).toHaveLength(1)                                       // nothing goes by itself after Stop
    await el.send('three')                                               // not ahead of "two"
    await tick(5)
    expect(lastUser(a.runs[1].input)).toBe('two')
    await a.release()
    expect(lastUser(a.runs[2].input)).toBe('three')
  })

  it('Edit keeps a half-typed draft; Remove can be undone', async () => {
    const el = await mount(), a = agent()
    el.agent = a as never
    void el.send('first')
    await tick(5)
    await el.send('queued text'); await el.send('another')
    const input = el.shadowRoot!.querySelector('textarea') as HTMLTextAreaElement
    input.value = 'my draft'
    ;($$(el, '.msg.queued')[0].querySelector('.q-edit') as HTMLButtonElement).click()
    expect(input.value).toBe('my draft\nqueued text')
    ;($$(el, '.msg.queued')[0].querySelector('.q-x') as HTMLButtonElement).click()
    expect($$(el, '.msg.queued')).toHaveLength(0)
    const undo = el.shadowRoot!.querySelector('.hint .btn.link') as HTMLButtonElement
    expect(undo.textContent).toBe('Undo')
    undo.click()
    expect($$(el, '.msg.queued').map((m) => m.querySelector('.bubble')!.textContent)).toEqual(['another'])
  })

  it('a double tap queues once; Esc stops the answer and brings the suggestions back', async () => {
    const el = await mount(), a = agent()
    el.agent = a as never
    ;(el as unknown as { _suggestions: string[] })._suggestions = ['Book a table']
    ;(el as unknown as { _renderQuick: () => void })._renderQuick()
    void el.send('Book a table')
    await tick(5)
    await el.send('again'); await el.send('again')
    expect($$(el, '.msg.queued')).toHaveLength(1)
    el.shadowRoot!.querySelector('textarea')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, composed: true }))
    await tick(20)
    expect(a.runs[0].aborted).toBe(true)
    expect($$(el, '.chip').map((c) => c.textContent)).toEqual(['Book a table'])
  })

  it('the page sets the suggestions without a run; [] clears them', async () => {
    const el = await mount()
    el.setSuggestions(['Add a note', 'Change the time'])
    expect($$(el, '.foot > .quick .chip').map((c) => c.textContent)).toEqual(['Add a note', 'Change the time'])
    el.setSuggestions([])
    expect(el.shadowRoot!.querySelector('.quick')).toBeNull()
  })

  it('the queue survives a reload', async () => {
    const el = await mount(), a = agent()
    el.agent = a as never
    void el.send('first')
    await tick(5)
    await el.send('kept')
    expect(JSON.parse(localStorage.getItem('agui-queue:q-test')!)[0].text).toBe('kept')
  })
})

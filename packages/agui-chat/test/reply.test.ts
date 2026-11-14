import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
type Obs = { next: (e: unknown) => void; complete: () => void }
/** An agent that answers with `reply` and records every run's input. */
const agent = (reply: string, seen: Record<string, unknown>[]) => ({
  run: (input: Record<string, unknown>) => ({ subscribe: (o: Obs) => {
    seen.push(input)
    setTimeout(() => {
      for (const e of [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, { type: 'TEXT_MESSAGE_START', messageId: `m${seen.length}`, role: 'assistant' },
        { type: 'TEXT_MESSAGE_CONTENT', messageId: `m${seen.length}`, delta: reply }, { type: 'TEXT_MESSAGE_END', messageId: `m${seen.length}` },
        { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]) o.next(e)
      o.complete()
    })
    return { unsubscribe() {} }
  } }),
})
async function mount(attrs: Record<string, string> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off', ...attrs })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]
/** Select `text` inside `node` the way a user would, then let the capsule appear. */
async function select(el: AguiChatElement, node: Element, text: string): Promise<void> {
  const t = [...node.querySelectorAll('*'), node].flatMap((n) => [...n.childNodes]).find((c) => c.nodeType === 3 && c.textContent!.includes(text))!
  const i = t.textContent!.indexOf(text)
  const range = document.createRange(); range.setStart(t, i); range.setEnd(t, i + text.length)
  const sel = document.getSelection()!; sel.removeAllRanges(); sel.addRange(range)
  document.dispatchEvent(new Event('selectionchange'))
  await tick(200)
  ;(el.shadowRoot!.querySelector('.cap-reply:not([hidden])') as HTMLButtonElement | null)?.click()   // step two: Reply opens the window
}

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals(); document.getSelection()?.removeAllRanges() })

/** The reply window's field, its buttons, and the composer's quote tiles. */
const pop = (el: AguiChatElement) => $(el, '.sel-pop') ?? ({ hidden: true } as HTMLElement)   // in the log only once shown
const field = (el: AguiChatElement) => $(el, '.pop-in') as HTMLTextAreaElement
const chips = (el: AguiChatElement) => $$(el, '.reply-chip')
const type = (f: HTMLTextAreaElement, text: string, key?: string) => {
  f.value = text; f.dispatchEvent(new Event('input'))
  if (key) f.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }))
}

describe('reply to a part of an answer', () => {
  it('a selection opens the reply window: the quote, "Reply to Assistant"; Enter adds it to the composer', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('The fee is 2% of the amount. It is paid once.', seen) as never
    await el.send('fees?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), 'The fee is 2%')
    expect(pop(el).hidden).toBe(false)
    expect($(el, '.pop-q').textContent).toBe('The fee is 2%')
    expect(field(el).placeholder).toBe('Reply to Assistant')
    expect($(el, '.pop-add').getAttribute('aria-label')).toBe('Add to chat')
    type(field(el), 'is that per month?', 'Enter')
    await tick(5)
    expect(pop(el).hidden).toBe(true)
    expect(seen).toHaveLength(1)                                            // nothing sent yet
    expect(chips(el)).toHaveLength(1)
    expect(chips(el)[0].querySelector('.rc-note-t')!.textContent).toBe('is that per month?')
    ;(chips(el)[0].querySelector('.rc-x') as HTMLButtonElement).click()
    await select(el, $(el, '.msg.ai .body'), 'The fee is 2%')
    type(field(el), '', 'Enter')
    await el.send('is that per month?')
    expect(seen[1].forwardedProps).toMatchObject({ reply_to: [{ message_id: 'm1', quote: 'The fee is 2%' }] })
    const bubble = [...el.shadowRoot!.querySelectorAll('.msg.me .bubble')].at(-1) as HTMLElement
    expect(bubble.querySelector('.bubble-q')!.textContent).toBe('The fee is 2%')
    expect(bubble.lastChild!.textContent).toBe('is that per month?')
    expect(chips(el)).toHaveLength(0)
    await tick(5)
    await el.send('and the next one?')
    expect(seen[2].forwardedProps).not.toHaveProperty('reply_to')   // one run only
  })

  it('Add to chat collects several quotes, each with its reply; one message carries them all', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('The fee is 2%. The term is 36 months. Insurance is optional.', seen) as never
    await el.send('terms?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), 'The fee is 2%')
    type(field(el), 'per month?')
    ;($(el, '.pop-add') as HTMLButtonElement).click()
    await select(el, $(el, '.msg.ai .body'), 'The term is 36 months')
    ;($(el, '.pop-add') as HTMLButtonElement).click()
    expect(chips(el).map((c) => c.querySelector('.rc-q')!.textContent)).toEqual(['“The fee is 2%”', '“The term is 36 months”'])
    expect(chips(el)[0].querySelector('.rc-note')!.textContent).toBe('With reply')   // only the first has a reply
    expect(chips(el)[1].querySelector('.rc-note')).toBeNull()
    ;(chips(el)[0].querySelector('.rc-note') as HTMLButtonElement).click()
    expect((chips(el)[0].querySelector('.rc-note-t') as HTMLElement).hidden).toBe(false)
    expect($(el, 'textarea:not(.pop-in)').getAttribute('aria-describedby')).toBe('reply-list')
    await el.send('and can I change them later?')
    expect((seen[1].forwardedProps as { reply_to: unknown[] }).reply_to).toEqual([
      { message_id: 'm1', quote: 'The fee is 2%', note: 'per month?' }, { message_id: 'm1', quote: 'The term is 36 months' }])
    const bubble = [...el.shadowRoot!.querySelectorAll('.msg.me .bubble')].at(-1) as HTMLElement
    expect([...bubble.querySelectorAll('.bubble-q')].map((q) => q.textContent)).toEqual(['The fee is 2%', 'The term is 36 months'])
    expect(bubble.querySelector('.bq-note')!.textContent).toBe('per month?')
    expect(chips(el)).toHaveLength(0)
  })

  it('quotes with their own replies go without a text of the composer', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('The fee is 2%.', seen) as never
    await el.send('fee?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), 'The fee is 2%')
    type(field(el), 'too high')
    ;($(el, '.pop-add') as HTMLButtonElement).click()
    ;($(el, '.send') as HTMLButtonElement).click()
    await tick(5)
    expect((seen[1].forwardedProps as { reply_to: unknown[] }).reply_to).toEqual([{ message_id: 'm1', quote: 'The fee is 2%', note: 'too high' }])
    const msgs = seen[1].messages as { role: string; content: string }[]
    expect(msgs.filter((m) => m.role === 'user').at(-1)!.content).toBe('My replies are on the quotes above.')   // a short text, so the turn has one
    const bubble = [...el.shadowRoot!.querySelectorAll('.msg.me .bubble')].at(-1) as HTMLElement
    expect(bubble.textContent).not.toContain('My replies are')                // not drawn in the bubble
  })

  it('closing the window never loses what was typed: a tap elsewhere keeps it as the reply to the quote', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('The fee is 2%.', seen) as never
    await el.send('fee?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), 'The fee is 2%')
    type(field(el), 'too high?')
    document.body.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, composed: true }))
    expect(pop(el).hidden).toBe(true)
    expect(chips(el)).toHaveLength(1)
    expect(chips(el)[0].querySelector('.rc-note-t')!.textContent).toBe('too high?')
  })

  it('a quote with a reply makes Send ready; removing a quote offers Undo', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('The fee is 2%.', seen) as never
    await el.send('fee?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), 'The fee is 2%')
    type(field(el), 'too high?', 'Enter')
    expect($(el, '.send').classList.contains('idle')).toBe(false)
    ;(chips(el)[0].querySelector('.rc-x') as HTMLButtonElement).click()
    expect(chips(el)).toHaveLength(0)
    const undo = $(el, '.hint .btn.link') as HTMLButtonElement
    expect(undo.textContent).toBe('Undo')
    undo.click()
    expect(chips(el)).toHaveLength(1)
    expect(chips(el)[0].querySelector('.rc-note-t')!.textContent).toBe('too high?')
  })

  it('a tap on the quote brings the answer back and highlights it', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('Opening hours are 9 to 6.', seen) as never
    await el.send('hours?')
    await tick(5)
    const answer = $(el, '.msg.ai')
    const into = vi.fn(); answer.scrollIntoView = into
    await select(el, $(el, '.msg.ai .body'), '9 to 6')
    type(field(el), '', 'Enter')
    await el.send('on Saturday too?')
    await tick(5)
    ;($(el, '.bubble-q') as HTMLButtonElement).click()
    expect(into).toHaveBeenCalledWith(expect.objectContaining({ block: 'center' }))
    expect(answer.classList.contains('flash')).toBe(true)
  })

  it('no window for your own message; Esc closes the window; Esc and x take quotes back', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('Sure, and more.', seen) as never
    await el.send('my own words here')
    await tick(5)
    await select(el, $(el, '.msg.me .bubble'), 'own words')
    expect(pop(el).hidden).toBe(true)
    await select(el, $(el, '.msg.ai .body'), 'Sure')
    field(el).dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(pop(el).hidden).toBe(true)
    await select(el, $(el, '.msg.ai .body'), 'Sure')
    ;($(el, '.pop-add') as HTMLButtonElement).click()
    await select(el, $(el, '.msg.ai .body'), 'and more')
    ;($(el, '.pop-add') as HTMLButtonElement).click()
    expect(chips(el)).toHaveLength(2)
    $(el, 'textarea:not(.pop-in)').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(chips(el).map((c) => c.querySelector('.rc-q')!.textContent)).toEqual(['“Sure”'])
    ;(chips(el)[0].querySelector('.rc-x') as HTMLButtonElement).click()
    expect(chips(el)).toHaveLength(0)
    expect($(el, '.reply-list').hidden).toBe(true)
  })

  it('a long selection is cut to 300 characters; reply="off" opens no window', async () => {
    const long = `${'word '.repeat(100)}end`
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent(long, seen) as never
    await el.send('long?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), long.slice(0, 450))
    type(field(el), '', 'Enter')
    await el.send('ok')
    await tick(5)
    const q = (seen[1].forwardedProps as { reply_to: { quote: string }[] }).reply_to[0].quote
    expect(q.length).toBeLessThanOrEqual(300)
    expect(q.endsWith('…')).toBe(true)
    el.setAttribute('reply', 'off')
    await tick(5)
    await select(el, [...el.shadowRoot!.querySelectorAll('.msg.ai .body')].at(-1)!, 'word word')
    expect(pop(el).hidden).toBe(true)
  })

  it('restored replies: a list or one old object, each quote drawn; never sent back in messages', async () => {
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
    el.plugins = [{ name: 'h', restore: async () => ({ messages: [
      { id: 'a1', role: 'assistant', content: 'The fee is 2%. The term is 36 months.' },
      { id: 'u1', role: 'user', content: 'monthly?', reply_to: { message_id: 'a1', quote: 'The fee is 2%' } },
      { id: 'u2', role: 'user', content: 'ok', reply_to: [{ message_id: 'a1', quote: 'The fee is 2%', note: 'high' }, { message_id: 'a1', quote: 'The term is 36 months' }] },
    ] }) }] as never
    document.body.appendChild(el)
    await tick(20)
    const bubbles = $$(el, '.msg.me .bubble')
    expect(bubbles[0].querySelector('.bubble-q')!.textContent).toBe('The fee is 2%')
    expect([...bubbles[1].querySelectorAll('.bubble-q')].map((q) => q.textContent)).toEqual(['The fee is 2%', 'The term is 36 months'])
    expect(bubbles[1].querySelector('.bq-note')!.textContent).toBe('high')
    const seen: Record<string, unknown>[] = []
    el.agent = agent('Yes.', seen) as never
    await el.send('thanks')
    expect((seen[0].messages as Record<string, unknown>[]).some((m) => 'reply_to' in m)).toBe(false)
  })
})

describe('more ways to reply', () => {
  it('Reply under an answer quotes the whole of it; a cut word at the edge of a selection is dropped', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('Opening hours are 9 to 6 on weekdays.', seen) as never
    await el.send('hours?')
    await tick(5)
    ;($(el, '.act-reply') as HTMLButtonElement).click()
    expect(chips(el)[0].querySelector('.rc-q')!.textContent).toBe('Assistant · Opening hours are 9 to 6 on weekdays.')
    await el.send('and on Saturday?')
    expect((seen[1].forwardedProps as { reply_to: unknown[] }).reply_to).toEqual([{ message_id: 'm1', whole: true }])
    expect([...el.shadowRoot!.querySelectorAll('.bubble-q')].at(-1)!.getAttribute('aria-label')).toContain('Reply to the whole answer')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), 'ng hours are 9 to 6 on wee')
    expect($(el, '.pop-q').textContent).toBe('hours are 9 to 6 on')
  })

  it('a restored quote whose answer is gone is plain text, not a button', async () => {
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
    el.plugins = [{ name: 'h', restore: async () => ({ messages: [{ id: 'u1', role: 'user', content: 'monthly?', reply_to: [{ message_id: 'gone', quote: 'The fee' }] }] }) }] as never
    document.body.appendChild(el)
    await tick(20)
    expect($(el, '.bubble-q').tagName).toBe('DIV')
  })
})

describe('long messages fold', () => {
  it('a tall bubble shows its start and Show more; Show less folds it again; short ones stay', async () => {
    const tall = vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function (this: HTMLElement) { return this.textContent!.length > 200 ? 600 : 40 })
    const shown = vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(40)
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('Ok.', seen) as never
    await el.send('short')
    await el.send('pasted '.repeat(60))
    const btns = [...el.shadowRoot!.querySelectorAll<HTMLButtonElement>('.fold-btn')]
    expect(btns).toHaveLength(1)
    const box = [...el.shadowRoot!.querySelectorAll<HTMLElement>('.msg.me .bubble')].at(-1)!
    expect(box.classList.contains('clamped')).toBe(true)
    expect(btns[0].textContent).toBe('Show more')
    expect(btns[0].getAttribute('aria-controls')).toBe(box.id)
    btns[0].click()
    expect(box.classList.contains('clamped')).toBe(false)
    expect(btns[0].textContent).toBe('Show less')
    expect(btns[0].getAttribute('aria-expanded')).toBe('true')
    btns[0].click()
    expect(box.classList.contains('clamped')).toBe(true)
    expect($$(el, '.msg.ai .fold-btn')).toHaveLength(0)
    tall.mockRestore(); shown.mockRestore()
  })
})

describe('the voice option', () => {
  it('off hides the mic; server records even where the browser could listen', async () => {
    vi.stubGlobal('webkitSpeechRecognition', class {})
    const el = await mount({ voice: 'off' })
    expect($(el, '.mic').hidden).toBe(true)
    el.setAttribute('voice', 'browser')
    expect($(el, '.mic').hidden).toBe(false)
    vi.stubGlobal('MediaRecorder', class {})
    vi.stubGlobal('navigator', { ...navigator, mediaDevices: { getUserMedia: async () => ({}) } })
    el.setAttribute('voice', 'auto')   // jsdom is not Chrome: auto records for the server
    expect((el as unknown as { _micMode: () => string })._micMode()).toBe('server')
  })

  it('auto prefers the server when its restore says it transcribes, even in Chrome', async () => {
    vi.stubGlobal('webkitSpeechRecognition', class {})
    vi.stubGlobal('chrome', {})
    vi.stubGlobal('MediaRecorder', class {})
    vi.stubGlobal('navigator', { ...navigator, userAgent: 'Mozilla/5.0 (Macintosh) Chrome/131', mediaDevices: { getUserMedia: async () => ({}) } })
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
    let say!: (v: unknown) => void
    el.plugins = [{ name: 'h', restore: () => new Promise((r) => { say = r }) }] as never
    document.body.appendChild(el)
    await tick()
    const mode = () => (el as unknown as { _micMode: () => string })._micMode()
    expect(mode()).toBe('browser')
    say({ messages: [], transcription: true })
    await tick(5)
    expect(mode()).toBe('server')
  })
})

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
/** Select `text` inside `node` the way a user would, then let the capsule appear. */
async function select(el: AguiChatElement, node: Element, text: string): Promise<void> {
  const t = [...node.querySelectorAll('*'), node].flatMap((n) => [...n.childNodes]).find((c) => c.nodeType === 3 && c.textContent!.includes(text))!
  const i = t.textContent!.indexOf(text)
  const range = document.createRange(); range.setStart(t, i); range.setEnd(t, i + text.length)
  const sel = document.getSelection()!; sel.removeAllRanges(); sel.addRange(range)
  document.dispatchEvent(new Event('selectionchange'))
  await tick(200)
}

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals(); document.getSelection()?.removeAllRanges() })

describe('reply to a part of an answer', () => {
  it('a selection in an answer offers Reply; the quote goes with the next message and shows above it', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('The fee is 2% of the amount. It is paid once.', seen) as never
    await el.send('fees?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), 'The fee is 2%')
    const pill = $(el, '.sel-pill')
    expect(pill.hidden).toBe(false)
    expect(pill.querySelector('.pill-t')!.textContent).toBe('Reply')
    ;(pill.querySelector('.pill-reply') as HTMLButtonElement).click()
    expect(pill.hidden).toBe(true)
    expect($(el, '.reply-bar').hidden).toBe(false)
    expect($(el, '.reply-q').textContent).toBe('The fee is 2%')
    expect(el.shadowRoot!.activeElement).toBe($(el, 'textarea'))
    await el.send('is that per month?')
    expect(seen[1].forwardedProps).toMatchObject({ reply_to: { message_id: 'm1', quote: 'The fee is 2%' } })
    expect($(el, '.reply-bar').hidden).toBe(true)
    const bubble = [...el.shadowRoot!.querySelectorAll('.msg.me .bubble')].at(-1) as HTMLElement
    expect(bubble.querySelector('.bubble-q')!.textContent).toBe('The fee is 2%')
    expect(bubble.lastChild!.textContent).toBe('is that per month?')
    await tick(5)
    await el.send('and the next one?')
    expect(seen[2].forwardedProps).not.toHaveProperty('reply_to')   // one run only
  })

  it('a tap on the quote brings the answer back and highlights it', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('Opening hours are 9 to 6.', seen) as never
    await el.send('hours?')
    await tick(5)
    const answer = $(el, '.msg.ai')
    const into = vi.fn(); answer.scrollIntoView = into
    await select(el, $(el, '.msg.ai .body'), '9 to 6')
    ;($(el, '.pill-reply') as HTMLButtonElement).click()
    await el.send('on Saturday too?')
    ;($(el, '.bubble-q') as HTMLButtonElement).click()
    expect(into).toHaveBeenCalledWith(expect.objectContaining({ block: 'center' }))
    expect(answer.classList.contains('flash')).toBe(true)
  })

  it('no capsule for your own message; Esc and the cross remove the quote', async () => {
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent('Sure.', seen) as never
    await el.send('my own words here')
    await tick(5)
    await select(el, $(el, '.msg.me .bubble'), 'own words')
    expect($(el, '.sel-pill').hidden).toBe(true)
    await select(el, $(el, '.msg.ai .body'), 'Sure')
    ;($(el, '.pill-reply') as HTMLButtonElement).click()
    $(el, 'textarea').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect($(el, '.reply-bar').hidden).toBe(true)
    await select(el, $(el, '.msg.ai .body'), 'Sure')
    ;($(el, '.pill-reply') as HTMLButtonElement).click()
    ;($(el, '.reply-x') as HTMLButtonElement).click()
    expect($(el, '.reply-bar').hidden).toBe(true)
  })

  it('a long selection is cut to 300 characters; reply="off" shows no capsule', async () => {
    const long = `${'word '.repeat(100)}end`
    const el = await mount(), seen: Record<string, unknown>[] = []
    el.agent = agent(long, seen) as never
    await el.send('long?')
    await tick(5)
    await select(el, $(el, '.msg.ai .body'), long.slice(0, 450))
    ;($(el, '.pill-reply') as HTMLButtonElement).click()
    await el.send('ok')
    const q = (seen[1].forwardedProps as { reply_to: { quote: string } }).reply_to.quote
    expect(q.length).toBeLessThanOrEqual(300)
    expect(q.endsWith('…')).toBe(true)
    el.setAttribute('reply', 'off')
    await tick(5)
    await select(el, [...el.shadowRoot!.querySelectorAll('.msg.ai .body')].at(-1)!, 'word word')
    expect($(el, '.sel-pill').hidden).toBe(true)
  })

  it('a restored reply shows its quote and is not sent back in messages', async () => {
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
    el.plugins = [{ name: 'h', restore: async () => ({ messages: [
      { id: 'a1', role: 'assistant', content: 'The fee is 2%.' },
      { id: 'u1', role: 'user', content: 'monthly?', reply_to: { message_id: 'a1', quote: 'The fee is 2%' } },
    ] }) }] as never
    document.body.appendChild(el)
    await tick(20)
    expect($(el, '.msg.me .bubble-q').textContent).toBe('The fee is 2%')
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
    expect($(el, '.reply-q').textContent).toBe('Opening hours are 9 to 6 on weekdays.')
    ;($(el, '.reply-x') as HTMLButtonElement).click()
    await select(el, $(el, '.msg.ai .body'), 'ng hours are 9 to 6 on wee')
    ;($(el, '.pill-reply') as HTMLButtonElement).click()
    expect($(el, '.reply-q').textContent).toBe('hours are 9 to 6 on')
  })

  it('a restored quote whose answer is gone is plain text, not a button', async () => {
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
    el.plugins = [{ name: 'h', restore: async () => ({ messages: [{ id: 'u1', role: 'user', content: 'monthly?', reply_to: { message_id: 'gone', quote: 'The fee' } }] }) }] as never
    document.body.appendChild(el)
    await tick(20)
    expect($(el, '.bubble-q').tagName).toBe('DIV')
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
})

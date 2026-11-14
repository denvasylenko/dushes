import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
type Obs = { next: (e: unknown) => void; complete: () => void }
/** An agent that answers every message with `reply`. */
const agent = (reply: string, hold?: Promise<void>) => ({
  run: () => ({ subscribe: (o: Obs) => {
    setTimeout(async () => {
      o.next({ type: 'RUN_STARTED', threadId: 't', runId: 'r' })
      await hold
      for (const e of [{ type: 'TEXT_MESSAGE_START', messageId: 'm1', role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: 'm1', delta: reply },
        { type: 'TEXT_MESSAGE_END', messageId: 'm1' }, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]) o.next(e)
      o.complete()
    })
    return { unsubscribe() {} }
  } }),
})
async function mount(attrs: Record<string, string> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off', ...attrs })) el.setAttribute(k, v)
  el.options = { upload: async (f: File) => ({ id: `att_${f.name}`, filename: f.name }) }
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]

beforeEach(() => {
  document.body.innerHTML = ''
  vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 })))
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:preview' }))
})
afterEach(() => { vi.unstubAllGlobals() })

describe('a sent message', () => {
  it('shows its images above the bubble, not inside it', async () => {
    const el = await mount()
    el.agent = agent('Got it') as never
    const picker = el.shadowRoot!.querySelector('input[type=file]') as HTMLInputElement
    Object.defineProperty(picker, 'files', { value: [new File(['x'], 'a.png', { type: 'image/png' })], configurable: true })
    picker.dispatchEvent(new Event('change'))
    await tick(20)
    await el.send('look')
    const msg = $(el, '.msg.me')
    expect([...msg.children].map((c) => c.classList[0])).toEqual(['att-row', 'bubble'])
    expect($(el, '.msg.me .bubble').textContent).toBe('look')
  })
})

describe('actions under an answer', () => {
  it('copy by default; your own list and your own action, with an event', async () => {
    const writeText = vi.fn(async () => {})
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const el = await mount()
    el.agent = agent('Hello **there**') as never
    await el.send('hi')
    await tick(5)
    expect($$(el, '.msg.ai .msg-acts .act').map((b) => b.getAttribute('aria-label'))).toEqual(['Copy', 'Reply'])
    ;($(el, '.act-copy') as HTMLButtonElement).click()
    await tick()
    expect(writeText).toHaveBeenCalledWith('Hello **there**')
    expect($(el, '.act-copy').classList.contains('done')).toBe(true)

    const seen: unknown[] = []
    el.addEventListener('agui:message-action', (e) => seen.push((e as CustomEvent).detail))
    el.options = { messageActions: ['copy', 'retry', 'like', 'dislike', { id: 'fork', label: 'Fork from here', hint: 'Starts a new chat from this point' }] }
    await el.send('again')
    await tick(5)
    const last = $$(el, '.msg.ai').at(-1)!
    expect([...last.querySelectorAll('.act')].map((b) => b.getAttribute('aria-label'))).toEqual(['Copy', 'Try again', 'Good answer', 'Bad answer', 'Fork from here'])
    expect(last.querySelector('.act-fork')!.getAttribute('title')).toBe('Fork from here\nStarts a new chat from this point')
    ;(last.querySelector('.act-like') as HTMLButtonElement).click()
    await tick()
    ;(last.querySelector('.act-dislike') as HTMLButtonElement).click()
    await tick()
    expect(last.querySelector('.act-like')!.getAttribute('aria-pressed')).toBe('false')   // one or the other
    expect(last.querySelector('.act-dislike')!.getAttribute('aria-pressed')).toBe('true')
    ;(last.querySelector('.act-fork') as HTMLButtonElement).click()
    await tick()
    expect(seen.map((d) => (d as { id: string }).id)).toEqual(['like', 'dislike', 'fork'])
    expect((seen[2] as { messageId: string; text: string })).toMatchObject({ messageId: 'm1', text: 'Hello **there**' })
    expect($$(el, '.act-retry')).toHaveLength(1)                               // "Try again" only under the latest answer
  })

  it('onMessageAction returning true replaces the built-in copy; "off" shows none', async () => {
    const writeText = vi.fn(async () => {})
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const el = await mount()
    const handled = vi.fn(() => true)
    el.options = { onMessageAction: handled }
    el.agent = agent('Hi') as never
    await el.send('hi')
    await tick(5)
    ;($(el, '.act-copy') as HTMLButtonElement).click()
    await tick()
    expect(handled).toHaveBeenCalledWith('copy', expect.objectContaining({ text: 'Hi' }))
    expect(writeText).not.toHaveBeenCalled()
    const off = await mount({ 'message-actions': 'off' })
    off.agent = agent('Hi') as never
    await off.send('hi')
    await tick(5)
    expect($$(off, '.msg-acts')).toHaveLength(0)
  })
})

describe('a panel beside the page', () => {
  it('modal: false drops the scrim and aria-modal, so the page beside it stays usable', async () => {
    const el = await mount({ mode: 'floating' })
    expect($(el, '.panel').getAttribute('aria-modal')).toBe('true')
    el.setAttribute('modal', 'off')
    expect($(el, '.wrap').classList.contains('nonmodal')).toBe(true)
    expect($(el, '.panel').hasAttribute('aria-modal')).toBe(false)
    el.options = { modal: true }
    expect($(el, '.panel').getAttribute('aria-modal')).toBe('true')
  })
})

describe('the launcher in every mode', () => {
  it('auto: a pill for the panel, a round button for the bubble; round, pill, none and its words are options', async () => {
    const el = await mount({ mode: 'floating' })
    const wrap = $(el, '.wrap'), fab = $(el, '.fab')
    expect(wrap.classList.contains('launcher-pill')).toBe(true)
    el.setAttribute('mode', 'bubble')
    expect(wrap.classList.contains('launcher-round')).toBe(true)
    el.options = { mode: 'floating', launcher: 'round' }
    expect(wrap.classList.contains('launcher-round')).toBe(true)
    el.options = { launcher: 'pill', launcherLabel: 'Edit with AI' }
    expect($(el, '.fab-label').textContent).toBe('Edit with AI')
    expect(fab.getAttribute('aria-label')).toBe('Edit with AI')
    el.setAttribute('launcher', 'none')
    expect(wrap.classList.contains('launcher-none')).toBe(true)   // the page's own button calls chat.open()
  })

  it('render.launcher replaces the content in the panel mode too', async () => {
    const el = await mount({ mode: 'floating' })
    el.options = { render: { launcher: () => { const s = document.createElement('span'); s.className = 'mine'; s.textContent = '✦ Herefront AI'; return s } } }
    expect($(el, '.fab').classList.contains('own')).toBe(true)
    expect($(el, '.fab-own .mine').textContent).toBe('✦ Herefront AI')
  })
})

describe('a lead taken back', () => {
  it('text_retract removes the lead written before the tools; the answer stays', async () => {
    const el = await mount()
    el.agent = { run: () => ({ subscribe: (o: Obs) => {
      setTimeout(() => {
        for (const e of [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' },
          { type: 'TEXT_MESSAGE_START', messageId: 'lead', role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: 'lead', delta: 'Sure. Let me look at the form first.' },
          { type: 'TEXT_MESSAGE_END', messageId: 'lead' },
          { type: 'CUSTOM', name: 'text_retract', value: { messageId: 'lead' } },
          { type: 'TEXT_MESSAGE_START', messageId: 'ans', role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: 'ans', delta: 'The form has two tabs.' },
          { type: 'TEXT_MESSAGE_END', messageId: 'ans' }, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]) o.next(e)
        o.complete()
      })
      return { unsubscribe() {} }
    } }) } as never
    await el.send('what is in it?')
    await tick(250)
    expect($$(el, '.msg.ai').map((m) => m.dataset.messageId)).toEqual(['ans'])
  })
})

describe('back to the latest message', () => {
  it('shows a jump button when scrolled up, with the dots while the assistant works', async () => {
    const el = await mount()
    let go!: () => void
    el.agent = agent('Done', new Promise<void>((r) => { go = r })) as never
    void el.send('hi')
    await tick(5)
    const log = $(el, '.log')
    Object.defineProperty(log, 'scrollHeight', { value: 2000, configurable: true })
    Object.defineProperty(log, 'clientHeight', { value: 400, configurable: true })
    log.scrollTop = 100
    log.dispatchEvent(new Event('scroll'))
    const jump = $(el, '.jump') as HTMLButtonElement
    expect(jump.hidden).toBe(false)
    expect(jump.classList.contains('busy')).toBe(true)                          // "•••": still answering below
    expect(jump.getAttribute('aria-label')).toBe('Jump to the latest')
    go()
    await tick(5)
    expect(jump.classList.contains('busy')).toBe(false)                         // the arrow again
    jump.click()
    expect(jump.hidden).toBe(true)
  })
})

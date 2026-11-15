import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
async function mount(options: Record<string, unknown> = {}, attrs: Record<string, string> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off', ...attrs })) el.setAttribute(k, v)
  el.options = options
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]
/** The menu's code loads on demand: wait until it is there (up to 2 s). */
const menu = async (el: AguiChatElement) => { for (let i = 0; i < 200 && !$(el, '.menu'); i++) await tick(10); return $(el, '.menu') }
const upload = async (f: File) => ({ id: `att_${f.name}`, filename: f.name })
const labels = (el: AguiChatElement) => $$(el, '.menu [role=menuitem]').map((b) => b.querySelector('.menu-l')!.firstChild!.textContent)

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('the + menu', () => {
  it('the + opens a menu, not the file picker; "Add files or photos" opens the picker; Esc closes it and gives the focus back', async () => {
    const el = await mount({ upload })
    const picker = $(el, 'input[type=file]') as HTMLInputElement
    const opened = vi.spyOn(picker, 'click').mockImplementation(() => {})
    const plus = $(el, '.clip') as HTMLButtonElement
    expect(plus.getAttribute('aria-label')).toBe('More')
    expect([plus.getAttribute('aria-haspopup'), plus.getAttribute('aria-expanded')]).toEqual(['menu', 'false'])   // said before the menu's code has loaded
    plus.click()
    const m = await menu(el)
    expect(opened).not.toHaveBeenCalled()                                  // the picker waits for its row
    expect(m.getAttribute('role')).toBe('menu')
    expect(plus.getAttribute('aria-expanded')).toBe('true')
    expect(labels(el)).toEqual(['Add files or photos'])
    m.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, composed: true }))
    expect($(el, '.menu')).toBeNull()
    expect(plus.getAttribute('aria-expanded')).toBe('false')
    expect(el.shadowRoot!.activeElement).toBe(plus)
    plus.click()
    await menu(el)
    $(el, '.menu [data-id=files]').click()
    expect(opened).toHaveBeenCalledTimes(1)
    expect($(el, '.menu')).toBeNull()                                      // a pick closes it
  })

  it('commands: a row that opens the host\'s list in place; a pick fires agui:menu-action and sends its text unless the host cancels', async () => {
    const el = await mount({ upload, commands: [{ id: 'hours', label: 'Opening hours', hint: 'When the shop is open', send: 'What are your opening hours?' }, { id: 'reset', label: 'Start over' }],
      menu: [{ id: 'template', label: 'Use a template' }] })
    const sent: string[] = []
    el.agent = { run: (i: { messages: { content: string }[] }) => ({ subscribe: (o: { next: (e: unknown) => void; complete: () => void }) => { sent.push(i.messages[i.messages.length - 1].content)
      setTimeout(() => { o.next({ type: 'RUN_STARTED', threadId: 't', runId: 'r' }); o.next({ type: 'RUN_FINISHED', threadId: 't', runId: 'r' }); o.complete() }); return { unsubscribe() {} } } }) } as never
    const picks: unknown[] = []
    el.addEventListener('agui:menu-action', (e) => { picks.push((e as CustomEvent).detail); if ((e as CustomEvent).detail.id === 'reset') e.preventDefault() })
    ;($(el, '.clip') as HTMLButtonElement).click()
    await menu(el)
    expect(labels(el)).toEqual(['Add files or photos', 'Commands', 'Use a template'])
    $(el, '.menu [data-id=commands]').click()                              // opens in place, with a way back
    expect(labels(el)).toEqual(['Commands', 'Opening hours', 'Start over'])
    expect($(el, '.menu [data-id=hours] .menu-h').textContent).toBe('When the shop is open')
    $(el, '.menu [data-id=hours]').click()
    await tick(20)
    expect(picks).toEqual([{ id: 'hours', label: 'Opening hours', command: true }])
    expect(sent).toEqual(['What are your opening hours?'])
    ;($(el, '.clip') as HTMLButtonElement).click()
    await menu(el)
    $(el, '.menu [data-id=template]').click()                              // the host's own row: an event, nothing sent
    expect(picks[1]).toEqual({ id: 'template', label: 'Use a template', command: false })
    expect(sent).toHaveLength(1)
  })

  it('"/" alone in the composer opens the commands; arrows move through the rows', async () => {
    const el = await mount({ commands: [{ id: 'a', label: 'First' }, { id: 'b', label: 'Second' }] })
    const input = $(el, 'textarea') as HTMLTextAreaElement
    input.value = '/'; input.dispatchEvent(new Event('input'))
    const m = await menu(el)
    expect(labels(el)).toEqual(['Commands', 'First', 'Second'])
    expect((el.shadowRoot!.activeElement as HTMLElement).dataset.id).toBe('a')   // the first command, not the way back
    m.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }))
    expect((el.shadowRoot!.activeElement as HTMLElement).dataset.id).toBe('b')
    ;(el.shadowRoot!.activeElement as HTMLElement).click()
    expect(input.value).toBe('')                                           // the slash that opened it is gone
  })

  it('no + when there is nothing to offer; with attachments off it still opens for commands', async () => {
    const none = await mount({ attach: false })
    expect($(none, '.clip').hidden).toBe(true)
    const some = await mount({ attach: false, upload, commands: [{ id: 'a', label: 'First' }] })
    expect($(some, '.clip').hidden).toBe(false)
    ;($(some, '.clip') as HTMLButtonElement).click()
    await menu(some)
    expect(labels(some)).toEqual(['Commands'])
  })
})

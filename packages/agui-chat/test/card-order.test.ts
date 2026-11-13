import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import type { AguiEvent } from '../src/types'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const agent = (events: AguiEvent[]) => ({ run: () => ({ subscribe: (o: { next: (e: AguiEvent) => void; complete: () => void }) => {
  setTimeout(() => { for (const e of events) o.next(e); o.complete() })
  return { unsubscribe: () => {} }
} }) })
const turn: AguiEvent[] = [
  { type: 'RUN_STARTED', threadId: 't', runId: 'r' },
  { type: 'TEXT_MESSAGE_START', messageId: 'm', role: 'assistant' },
  { type: 'TEXT_MESSAGE_CONTENT', messageId: 'm', delta: 'Which loan do you need? Here are the options for you.' },
  { type: 'TEXT_MESSAGE_END', messageId: 'm' },
  { type: 'CUSTOM', name: 'on_interrupt', value: { type: 'ask', card_id: 'q1', question: 'Which loan?', allow_text: false,
    options: [{ id: 'a', label: 'Car' }, { id: 'b', label: 'Cash' }] } },
  { type: 'RUN_FINISHED', threadId: 't', runId: 'r' },
]

async function mount(typing: string): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing, lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
  el.options = { typingSpeed: 120, fadeMs: 50 }
  el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
  el.agent = agent(turn)
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s)

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('cards come after their text', () => {
  it('waits for the typing to finish, then shows the card below the text', async () => {
    const el = await mount('words')
    void el.send('loan')
    await tick(60)
    expect($(el, '.msg.ai')).not.toBeNull()
    expect($(el, '.card')).toBeNull()                       // the sentence is still typing: no card under it yet
    await tick(1500)
    const card = $(el, '.card')!
    expect(card).not.toBeNull()
    const msg = $(el, '.msg.ai')!
    expect(msg.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('shows the card at once when the text is not typed', async () => {
    const el = await mount('plain')
    void el.send('loan')
    await tick(30)
    expect($(el, '.card')).not.toBeNull()
  })
})

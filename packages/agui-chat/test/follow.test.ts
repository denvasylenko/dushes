import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import { blocksCard } from '../src/formguide/blocks'
import type { AguiEvent, Plugin } from '../src/types'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))

/** Herefront's follow after a reload: text that a cut takes back, tools, a card, the answer in pieces, more tools. */
async function* follow(): AsyncIterable<AguiEvent> {
  yield { type: 'RUN_STARTED', threadId: 't', runId: 'r' }
  yield { type: 'TEXT_MESSAGE_START', messageId: 'follow-m1', role: 'assistant' }
  yield { type: 'TEXT_MESSAGE_CONTENT', messageId: 'follow-m1', delta: 'Let me look that up.' }
  yield { type: 'TEXT_MESSAGE_END', messageId: 'follow-m1' }
  yield { type: 'CUSTOM', name: 'hf_cut', value: { messageId: 'follow-m1' } }
  yield { type: 'TOOL_CALL_START', toolCallId: 'c1', toolCallName: 'find_place' }
  yield { type: 'TOOL_CALL_END', toolCallId: 'c1' }
  yield { type: 'CUSTOM', name: 'card', value: { type: 'blocks', name: 'found', blocks: [{ type: 'place', title: 'Bar Centrale' }] } }
  yield { type: 'TEXT_MESSAGE_START', messageId: 'follow-m3', role: 'assistant' }
  for (const w of 'Found it: Bar Centrale on Corso Umberto, open until midnight.'.split(/(?<= )/)) {
    yield { type: 'TEXT_MESSAGE_CONTENT', messageId: 'follow-m3', delta: w }
    await tick(1)
  }
  yield { type: 'TEXT_MESSAGE_END', messageId: 'follow-m3' }
  yield { type: 'TOOL_CALL_START', toolCallId: 'c2', toolCallName: 'build_site' }
  yield { type: 'TOOL_CALL_END', toolCallId: 'c2' }
  yield { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }
}

beforeEach(() => { document.body.innerHTML = ''; localStorage.clear(); vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

/** Herefront's raw follow dump, in its order and shape (cards first, then 27 text pieces, all in one burst: the turn
 *  had already finished); the Italian text is replaced by English (the repository is English-only). */
function dump(): AguiEvent[] {
  const words = 'The restaurant is open today until eleven. Call them to book a table for tonight. The prices shown are only examples of this preview.'
    .split(/(?<= )/)
  return [
    { type: 'RUN_STARTED', threadId: 'T', runId: 'follow' },
    { type: 'TOOL_CALL_START', toolCallId: 'follow-t1', toolCallName: 'contact' }, { type: 'TOOL_CALL_END', toolCallId: 'follow-t1' },
    { type: 'TOOL_CALL_RESULT', toolCallId: 'follow-t1', messageId: 'follow-t1-r', content: '' } as AguiEvent,
    { type: 'TOOL_CALL_START', toolCallId: 'follow-t2', toolCallName: 'show_items' }, { type: 'TOOL_CALL_END', toolCallId: 'follow-t2' },
    { type: 'TOOL_CALL_RESULT', toolCallId: 'follow-t2', messageId: 'follow-t2-r', content: '' } as AguiEvent,
    { type: 'CUSTOM', name: 'card', value: { card_id: 'follow-c3', name: 'hf-call', blocks: [{ type: 'links', items: [{ kind: 'call', label: 'Call', value: '+39085123456' }] }] } },
    { type: 'CUSTOM', name: 'card', value: { card_id: 'follow-c4', name: 'hf-items', blocks: [{ type: 'title', text: 'Ask on the phone' }, { type: 'row', label: 'Home-made pasta', value: '12' }] } },
    { type: 'TEXT_MESSAGE_START', messageId: 'follow-m5', role: 'assistant' },
    ...words.map((w) => ({ type: 'TEXT_MESSAGE_CONTENT', messageId: 'follow-m5', delta: w }) as AguiEvent),
    { type: 'TEXT_MESSAGE_END', messageId: 'follow-m5' },
    { type: 'RUN_FINISHED', threadId: 'T', runId: 'follow' },
  ]
}

describe('no animation frames (a hidden pane, an occluded window)', () => {
  it('puts the text in at once instead of leaving the bubble empty', async () => {
    vi.stubGlobal('requestAnimationFrame', () => 1)   // frames never come
    vi.stubGlobal('cancelAnimationFrame', () => {})
    const el = document.createElement('agui-chat') as AguiChatElement
    el.options = { mode: 'bubble', typing: 'words', lang: 'en', persistThread: false }
    const host: Plugin = { name: 'h', restore: async () => ({ messages: [{ id: 'u1', role: 'user', content: 'Is it open today?' }],
      follow: async function* () { for (const e of dump()) yield e } }), onEvent: (ev) => ev.type === 'CUSTOM' && ev.name === 'card' }
    el.use(host)
    document.body.appendChild(el)
    await tick(600)
    expect(el.shadowRoot!.querySelector('.msg.ai')!.textContent).toContain('The prices shown are only examples of this preview.')
  })
})

describe('cards after a reload', () => {
  it('an activity message draws its card again in its place, and is not sent back as history', async () => {
    const el = document.createElement('agui-chat') as AguiChatElement
    el.options = { mode: 'inline', typing: 'plain', lang: 'en', persistThread: false }
    const seen: AguiEvent[] = []
    const route = { type: 'blocks', name: 'route', blocks: [{ type: 'text', text: 'Arbat 12' }] }
    const host: Plugin = { name: 'h', restore: async () => ({ messages: [
      { id: 'u1', role: 'user', content: 'How do I get there?' }, { id: 'a1', role: 'assistant', content: 'Here is the route.' },
      { id: 'c1', role: 'activity', activityType: 'card', activity: route }] }),
    onEvent: (ev) => { seen.push(ev); return ev.type === 'CUSTOM' && ev.name === 'card' } }
    el.use(host)
    document.body.appendChild(el)
    await tick(50)
    expect(seen).toEqual([expect.objectContaining({ type: 'CUSTOM', name: 'card', value: route })])
    expect((el as unknown as { _messages: { role: string }[] })._messages.map((m) => m.role)).toEqual(['user', 'assistant'])
  })
})

describe('follow after a reload', () => {
  for (const typing of ['words', 'plain']) {
    it(`plays Herefront's dump: cards, then the text in one burst (${typing})`, async () => {
      const el = document.createElement('agui-chat') as AguiChatElement
      el.options = { mode: 'bubble', typing: typing as 'words', lang: 'en', history: 'last', persistThread: true }
      const host: Plugin = { name: 'herefront-site',
        restore: async () => ({ messages: [{ id: 'u1', role: 'user', content: 'Is it open today?' }], follow: async function* () { for (const e of dump()) yield e } }),
        onEvent: (ev, chat) => {   // their display cards, as in hf-agui.js
          if (ev.type !== 'CUSTOM' || ev.name !== 'card') return
          const rc = { chat, t: chat.t.bind(chat), resolve: () => {}, flags: {}, restored: false }
          const box = blocksCard(ev.value as Record<string, unknown>, rc, null)
          box.classList.add('card')
          chat.append(box)
          return true
        } }
      el.use(host)
      document.body.appendChild(el)
      await tick(1500)
      const ai = [...el.shadowRoot!.querySelectorAll('.msg.ai')].map((m) => m.textContent ?? '')
      expect(ai.join(' ')).toContain('The prices shown are only examples of this preview.')
      expect(el.shadowRoot!.querySelectorAll('.card').length).toBe(2)
    })
  }

  for (const typing of ['words', 'plain']) {
    it(`shows the followed text (${typing}), as the host wires it`, async () => {
      const el = document.createElement('agui-chat') as AguiChatElement
      for (const [k, v] of Object.entries({ mode: 'bubble', typing, lang: 'en', 'thread-id': 'sid-1' })) el.setAttribute(k, v)
      document.body.appendChild(el)   // the host appends first, then adds its plugins
      await tick()
      const fg = formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}), exclude: ['ask', 'upload', 'confirm', 'review'] })
      delete fg.restore
      el.use(fg)
      const host: Plugin = { name: 'herefront', restore: async () => ({ messages: [{ id: 'u1', role: 'user', content: 'Bar Centrale, Pescara' }], follow }),
        onEvent: (ev, chat) => {   // their cut, as in hf-agui.js
          if (ev.type !== 'CUSTOM' || ev.name !== 'hf_cut') return
          const id = (ev.value as { messageId?: string })?.messageId
          if (id && chat.removeMessage(id)) return true
          const all = chat.host.shadowRoot!.querySelectorAll('.msg.ai')
          if (all.length) all[all.length - 1].remove()
          return true
        } }
      el.use(host)
      await tick(400)
      const ai = [...el.shadowRoot!.querySelectorAll('.msg.ai')].map((m) => m.textContent)
      expect(ai.join(' ')).toContain('Found it: Bar Centrale on Corso Umberto, open until midnight.')
      expect(el.shadowRoot!.querySelectorAll('.msg.ai').length).toBe(1)
      expect(el.shadowRoot!.querySelector('.bk-place')).not.toBeNull()
      expect(el.shadowRoot!.querySelector('.wrap')!.classList.contains('open')).toBe(true)   // a bubble opens for a running turn
    })
  }
})

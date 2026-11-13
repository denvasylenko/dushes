import { afterEach, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import type { AguiEvent } from '../src/types'

const sse = (events: AguiEvent[]) => new Response(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(''),
  { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = '' })

it('a late history does not wipe a conversation that started meanwhile', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => sse([{ type: 'RUN_STARTED', threadId: 't', runId: 'r' },
    { type: 'TEXT_MESSAGE_START', messageId: 'm', role: 'assistant' },
    { type: 'TEXT_MESSAGE_CONTENT', messageId: 'm', delta: 'The live answer.' },
    { type: 'TEXT_MESSAGE_END', messageId: 'm' }, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }])))
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'off', 'persist-thread': 'off' })) el.setAttribute(k, v)
  document.body.appendChild(el)
  let release!: () => void
  el.use({ name: 'slow', restore: () => new Promise((ok) => { release = () => ok({ messages: [{ id: 'old', role: 'user', content: 'old question' }] }) }) })
  await tick()
  await el.send('new question')
  release()
  await tick(5)
  const log = el.shadowRoot!.querySelector('.log')!.textContent!
  expect(log).toContain('The live answer.')
  expect(log).not.toContain('old question')
})

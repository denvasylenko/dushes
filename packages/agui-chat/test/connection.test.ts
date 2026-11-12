import { afterEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import type { AguiEvent } from '../src/types'

// The chat's connection: headers (object or function), credentials, fetch, the request hook, a transport.

const run = (...body: AguiEvent[]): AguiEvent[] => [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, ...body,
  { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]
const text = (s: string): AguiEvent[] => [{ type: 'TEXT_MESSAGE_START', messageId: 'm', role: 'assistant' },
  { type: 'TEXT_MESSAGE_CONTENT', messageId: 'm', delta: s }, { type: 'TEXT_MESSAGE_END', messageId: 'm' }]
const sse = (events: AguiEvent[]) => new Response(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(''),
  { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))

type Call = { url: string; init: RequestInit }
function recorder(reply: (c: Call) => Response = () => sse(run())) {
  const calls: Call[] = []
  return { calls, fetch: vi.fn(async (url: string, init: RequestInit) => { const c = { url, init }; calls.push(c); return reply(c) }) }
}
const hdr = (c: Call, k: string) => (c.init.headers as Record<string, string>)[k]

async function mount(): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off' })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  return el
}
const $ = (el: AguiChatElement, sel: string) => el.shadowRoot!.querySelector(sel) as HTMLElement

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = '' })

describe('connection', () => {
  it('calls an async headers function before every run, with the kind, through the host fetch', async () => {
    const global = vi.fn(); vi.stubGlobal('fetch', global)
    const r = recorder()
    let n = 0
    const el = await mount()
    el.options = { fetch: r.fetch, credentials: 'include', headers: async ({ kind }) => ({ Authorization: `Bearer t${++n}`, 'X-Kind': kind }) }
    await el.send('one')
    await el.send('two')
    expect(global).not.toHaveBeenCalled()
    expect(r.calls.map((c) => hdr(c, 'Authorization'))).toEqual(['Bearer t1', 'Bearer t2'])   // a fresh token each time
    expect(hdr(r.calls[0], 'X-Kind')).toBe('run')
    expect(hdr(r.calls[0], 'Content-Type')).toBe('application/json')                          // the transport's own stay
    expect(r.calls[0].init.credentials).toBe('include')
  })

  it('lets the request hook change the URL and init last', async () => {
    const r = recorder()
    const el = await mount()
    el.options = { fetch: r.fetch, headers: { 'X-Tenant': 'bank-1' },
      request: ({ kind, url, init }) => ({ url: `${url}?via=${kind}`, init: { ...init, keepalive: true } }) }
    await el.send('hi')
    expect(r.calls[0].url).toBe('/agent/run?via=run')
    expect(r.calls[0].init.keepalive).toBe(true)
    expect(hdr(r.calls[0], 'X-Tenant')).toBe('bank-1')
  })

  it('runs through an own transport, with no network request', async () => {
    const global = vi.fn(); vi.stubGlobal('fetch', global)
    const el = await mount()
    el.options = { transport: async function* () { yield* run(...text('From the transport.')) } }
    await el.send('hi')
    expect(global).not.toHaveBeenCalled()
    expect($(el, '.log').textContent).toContain('From the transport.')
  })

  it('shows a readable error when the headers function fails', async () => {
    const r = recorder()
    const el = await mount()
    const errors: string[] = []
    el.addEventListener('agui:error', (e) => errors.push(String((e as CustomEvent).detail)))
    el.options = { fetch: r.fetch, headers: async () => { throw new Error('token expired') } }
    await el.send('hi')
    expect(r.calls).toHaveLength(0)
    expect($(el, '.error')).not.toBeNull()
    expect(errors[0]).toContain('token expired')
  })

  it('sends the plugin requests (attachments, thread, feedback) through the same connection', async () => {
    const r = recorder((c) => c.url.includes('/threads/') ? new Response('{"messages":[]}', { status: 200 })
      : c.url.endsWith('/attachments') ? new Response('{"id":"att_1","filename":"p.pdf"}', { status: 200 }) : sse(run()))
    const el = await mount()
    el.options = { fetch: r.fetch, headers: ({ kind }) => ({ Authorization: 'Bearer x', 'X-Kind': kind }) }
    el.use(formguide({ getState: () => ({ config: {}, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
    await tick(5)
    const thread = r.calls.find((c) => c.url.includes('/threads/'))!
    expect(hdr(thread, 'Authorization')).toBe('Bearer x')
    expect(hdr(thread, 'X-Kind')).toBe('thread')
    const res = await el.request('attachments', '/agent/attachments', { method: 'POST', body: new FormData() })
    expect(res.ok).toBe(true)
    expect(hdr(r.calls.at(-1)!, 'X-Kind')).toBe('attachments')
  })
})

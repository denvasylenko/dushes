import { afterEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { capabilitiesFor, formguide } from '../src/formguide/index'

const finished = 'data: {"type":"RUN_STARTED","threadId":"t","runId":"r"}\n\ndata: {"type":"RUN_FINISHED","threadId":"t","runId":"r"}\n\n'

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = '' })

describe('formguide exclude', () => {
  it('announces the base cards and every variant by default', () => {
    const all = capabilitiesFor()
    expect(all).toEqual(expect.arrayContaining(['ask', 'upload', 'confirm', 'review', 'ask.range', 'upload.camera']))
  })

  it('leaves out an excluded card with its variants, or a single variant', () => {
    const caps = capabilitiesFor(['upload', 'review', 'ask.range'])
    expect(caps).not.toContain('upload')
    expect(caps.some((c) => c.startsWith('upload.'))).toBe(false)
    expect(caps).not.toContain('review')
    expect(caps).not.toContain('ask.range')
    expect(caps).toEqual(expect.arrayContaining(['ask', 'ask.details', 'confirm']))
  })

  it('sends the narrowed list with every run', async () => {
    const bodies: any[] = [] // eslint-disable-line @typescript-eslint/no-explicit-any
    vi.stubGlobal('fetch', vi.fn(async (_u: string, init?: RequestInit) => {
      bodies.push(JSON.parse(String(init?.body)))
      return new Response(finished, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
    }))
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off' })) el.setAttribute(k, v)
    document.body.appendChild(el)
    el.use(formguide({ getState: () => ({ config: {}, jsx_hash: 'h' }), applyChanges: async () => ({}), exclude: ['review'] }))
    await el.send('hi')
    const caps = bodies[0].forwardedProps.capabilities as string[]
    expect(caps).toContain('ask')
    expect(caps).not.toContain('review')
  })

  it('sends the page trace context with every run', async () => {
    const bodies: any[] = [] // eslint-disable-line @typescript-eslint/no-explicit-any
    vi.stubGlobal('fetch', vi.fn(async (_u: string, init?: RequestInit) => {
      bodies.push(JSON.parse(String(init?.body)))
      return new Response(finished, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
    }))
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', 'persist-thread': 'off' })) el.setAttribute(k, v)
    document.body.appendChild(el)
    const tp = '00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01'
    el.use(formguide({ getState: () => ({ config: {}, jsx_hash: 'h' }), applyChanges: async () => ({}), traceparent: () => tp }))
    await el.send('hi')
    expect(bodies[0].forwardedProps.traceparent).toBe(tp)
  })
})

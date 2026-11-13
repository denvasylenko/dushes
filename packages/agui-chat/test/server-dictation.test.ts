import { afterEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

// dictation: server | auto — the chat records, posts the audio to /transcribe and fills the input.

class FakeRecorder {
  static last: FakeRecorder | null = null
  static isTypeSupported = (t: string) => t.startsWith('audio/webm')
  state = 'inactive'
  mimeType = 'audio/webm;codecs=opus'
  ondataavailable: ((e: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  constructor() { FakeRecorder.last = this }
  start() { this.state = 'recording' }
  stop() {
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob(['opus'], { type: 'audio/webm' }) })
    setTimeout(() => this.onstop?.())
  }
}

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
const calls: { url: string; body: FormData }[] = []

function setup(answer: () => Response, withSpeech = false) {
  calls.length = 0
  vi.stubGlobal('MediaRecorder', FakeRecorder)
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true,
    value: { getUserMedia: vi.fn(async () => ({ getTracks: () => [{ stop() {} }] })) } })
  if (!withSpeech) { vi.stubGlobal('SpeechRecognition', undefined); vi.stubGlobal('webkitSpeechRecognition', undefined) }
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), body: init?.body as FormData })
    return answer()
  }))
}

async function mount(opts: Record<string, unknown>): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  el.setAttribute('mode', 'inline')
  el.setAttribute('persist-thread', 'off')
  document.body.appendChild(el)
  el.options = { url: '/agent/run', lang: 'en', ...opts }
  await tick()
  return el
}
const $ = (el: AguiChatElement, sel: string) => el.shadowRoot!.querySelector(sel) as HTMLElement

afterEach(() => { document.body.innerHTML = ''; vi.unstubAllGlobals() })

describe('server dictation', () => {
  it('records, shows the wave, transcribes and fills the input without sending', async () => {
    setup(() => new Response(JSON.stringify({ text: 'a car loan please', language: 'ru' }), { status: 200 }))
    const el = await mount({ dictation: 'server', micLang: 'ru' })
    const mic = $(el, '.mic')
    expect(mic.hidden).toBe(false)
    mic.click()
    await tick()
    expect($(el, '.box').classList.contains('rec')).toBe(true)
    expect(mic.classList.contains('on')).toBe(true)
    expect(mic.innerHTML).not.toContain('M5 11')                   // a stop square on red, not the mic glyph
    mic.click()                                                    // stop: transcribe
    await tick(); await tick()
    expect(calls[0].url).toMatch(/\/agent\/transcribe$/)
    expect(calls[0].body.get('language')).toBe('ru')
    expect(($(el, 'textarea') as HTMLTextAreaElement).value).toBe('a car loan please')
    expect($(el, '.box').classList.contains('rec')).toBe(false)
    expect(calls.length).toBe(1)                                   // nothing was sent to the agent
  })

  it('a failure says so and Try again posts the same recording', async () => {
    let n = 0
    setup(() => (n++ ? new Response(JSON.stringify({ text: 'second time' })) : new Response('down', { status: 502 })))
    const el = await mount({ dictation: 'server' })
    $(el, '.mic').click(); await tick()
    $(el, '.mic').click(); await tick(); await tick()
    expect($(el, '.hint').textContent).toContain("Couldn't transcribe")
    ;($(el, '.hint button') as HTMLButtonElement).click()
    await tick(); await tick()
    expect(calls.length).toBe(2)
    expect(($(el, 'textarea') as HTMLTextAreaElement).value).toBe('second time')
  })

  it('cancel drops the recording', async () => {
    setup(() => new Response(JSON.stringify({ text: 'never' })))
    const el = await mount({ dictation: 'server' })
    $(el, '.mic').click(); await tick()
    $(el, '.rec-x').click(); await tick(); await tick()
    expect(calls.length).toBe(0)
    expect($(el, '.box').classList.contains('rec')).toBe(false)
  })

  it('auto records for the server where the browser has no recognition', async () => {
    setup(() => new Response(JSON.stringify({ text: 'ok' })))
    const el = await mount({ dictation: 'auto', transcribeUrl: '/speech' })
    $(el, '.mic').click(); await tick()
    $(el, '.mic').click(); await tick(); await tick()
    expect(calls[0].url).toBe('/speech')
  })

  it('browser dictation stays the default: no recognition, no mic', async () => {
    setup(() => new Response('{}'))
    const el = await mount({})
    expect($(el, '.mic').hidden).toBe(true)
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

// The voice mode against a mock voice server and a fake microphone: no provider, nothing paid.
const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
type Obs = { next: (e: unknown) => void; complete: () => void }
const enc = new TextEncoder()

/** The host's voice endpoint, as the contract says: unlock, session, events, end. */
function server(opts: { code?: string; session?: () => Response } = {}) {
  const calls: { path: string; body: Record<string, unknown>; pass: string | null }[] = []
  let push: (ev: Record<string, unknown>) => void = () => {}
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url, 'http://host.test').pathname + new URL(url, 'http://host.test').search
    const pass = new Headers(init?.headers).get('X-Voice-Pass')
    const body = init?.body ? JSON.parse(String(init.body)) : {}
    calls.push({ path, body, pass })
    const json = (d: unknown, status = 200) => new Response(JSON.stringify(d), { status, headers: { 'Content-Type': 'application/json' } })
    if (path === '/voice/unlock') return body.code === (opts.code ?? 'DUSH26') ? json({ person: 'Anna', pass: 'pass-1' }) : json({ detail: 'no' }, 403)
    if (path === '/voice/session') return opts.session ? opts.session() : json({ talk: `t${calls.filter((c) => c.path === '/voice/session').length}`, sdp: 'answer-sdp', limits: { seconds: 300, silence_seconds: 60 } })
    if (path.startsWith('/voice/events')) return new Response(new ReadableStream<Uint8Array>({ start(c) {
      push = (ev) => c.enqueue(enc.encode(`data: ${JSON.stringify(ev)}\n\n`)); c.enqueue(enc.encode(': keep-alive\n\n')) } }))
    if (path === '/voice/end') return json({ cost_usd: 0.02 })
    return new Response(null, { status: 404 })
  })
  return { fetch, calls, push: (ev: Record<string, unknown>) => push(ev), ends: () => calls.filter((c) => c.path === '/voice/end').map((c) => c.body.talk) }
}
/** A microphone and a peer connection that do nothing but answer. `gate`: the permission prompt stays open until it resolves. */
function fakeAudio(gate?: Promise<void>) {
  const live = { mics: 0 }, peers: { closed: boolean; channel: string; remote?: string }[] = []
  vi.stubGlobal('navigator', { ...navigator, mediaDevices: { getUserMedia: async () => { await gate; live.mics++; return { getTracks: () => [{ stop: () => { live.mics-- } }] } } } })
  vi.stubGlobal('RTCPeerConnection', class {
    me = { closed: false, channel: '' } as { closed: boolean; channel: string; remote?: string }
    localDescription = { sdp: 'offer-sdp' }; ontrack: unknown = null
    constructor() { peers.push(this.me) }
    addTrack() {} createDataChannel(n: string) { this.me.channel = n }
    async createOffer() { return { type: 'offer', sdp: 'offer-sdp' } }
    async setLocalDescription() {} async setRemoteDescription(d: { sdp: string }) { this.me.remote = d.sdp }
    close() { this.me.closed = true }
  })
  return { live, peers, open: () => peers.filter((p) => !p.closed).length }
}
function agent(ms = 30) {
  const said: string[] = []
  return { said, run: (input: { messages: { role: string; content: string }[] }) => ({ subscribe: (o: Obs) => {
    said.push(input.messages.filter((m) => m.role === 'user').at(-1)!.content)
    const t = setTimeout(() => { for (const e of [{ type: 'RUN_STARTED' }, { type: 'TEXT_MESSAGE_START', messageId: `a${said.length}`, role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId: `a${said.length}`, delta: 'Done.' },
      { type: 'TEXT_MESSAGE_END', messageId: `a${said.length}` }, { type: 'RUN_FINISHED' }]) o.next(e); o.complete() }, ms)
    return { unsubscribe() { clearTimeout(t) } } } }) }
}
async function mount(attrs: Record<string, string> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off', 'thread-id': 'voice-1', url: 'http://host.test/agent/run', 'voice-mode': '', ...attrs })) el.setAttribute(k, v)
  document.body.appendChild(el)
  for (let i = 0; i < 100 && !el.shadowRoot!.querySelector('.vo-go'); i++) await tick(10)   // the voice file comes on demand
  return el
}
const $ = <T extends HTMLElement>(el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as T
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]
const pick = (el: AguiChatElement) => el.dispatchEvent(new CustomEvent('agui:menu-action', { detail: { id: 'agui-voice' }, cancelable: true, bubbles: true, composed: true }))
const enter = async (el: AguiChatElement, code: string) => { const i = $<HTMLInputElement>(el, '.vo-sheet input'); i.value = code; i.dispatchEvent(new Event('input')); $(el, '.vo-sheet').dispatchEvent(new Event('submit', { cancelable: true })); await tick(30) }
/** A chat whose person has entered the code before, in a voice conversation. */
async function talking(s: ReturnType<typeof server>, a?: ReturnType<typeof agent>) {
  vi.stubGlobal('fetch', s.fetch)
  sessionStorage.setItem('agui-voice-pass', 'pass-1')
  const el = await mount()
  if (a) el.agent = a as never
  $(el, '.vo-go').click()
  await tick(30)
  return el
}

beforeEach(() => { document.body.innerHTML = ''; localStorage.clear(); sessionStorage.clear() })
afterEach(() => { vi.unstubAllGlobals() })

describe('the experimental voice mode', () => {
  it('is not there unless the host turned it on (the dictation option `voice` is something else)', async () => {
    vi.stubGlobal('fetch', server().fetch)
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', lang: 'en', 'persist-thread': 'off', voice: 'server' })) el.setAttribute(k, v)
    document.body.appendChild(el)
    await tick(60)
    expect($(el, '.vo-go')).toBeNull()
    expect(el.options.menu ?? []).toEqual([])
  })

  it('the way in: a row in the + menu, the code, and voice starts; a wrong code says so', async () => {
    const s = server(), audio = fakeAudio()
    vi.stubGlobal('fetch', s.fetch)
    const el = await mount()
    expect(el.options.menu).toEqual([expect.objectContaining({ id: 'agui-voice', label: 'Experimental voice mode', hint: 'Needs your code' })])
    expect($(el, '.vo-go').hidden).toBe(true)                                   // no code yet: no orb
    expect(pick(el)).toBe(false)                                                // the chat handles its own row
    const sheet = $(el, '.vo-sheet'), ok = $<HTMLButtonElement>(el, '.vo-sheet button[type=submit]')
    expect(sheet.getAttribute('role')).toBe('dialog')
    expect(ok.textContent).toBe('Activate Experimental Mode')
    expect(ok.disabled).toBe(true)                                              // nothing typed
    await enter(el, 'WRONG')
    expect($(el, '.vo-err').textContent).toBe('That code did not work')
    expect(sheet.classList.contains('bad')).toBe(true)
    expect($(el, '.vo-sheet input').getAttribute('aria-invalid')).toBe('true')
    await enter(el, 'DUSH26')
    expect($(el, '.vo-sheet')).toBeNull()
    expect(sessionStorage.getItem('agui-voice-pass')).toBe('pass-1')            // kept for this browser session
    expect(el.options.menu![0].hint).toBeUndefined()
    expect($(el, '.foot').classList.contains('vo-on')).toBe(true)               // they asked for voice: it starts, no second tap
    expect(audio.open()).toBe(1)
    expect(s.calls.map((c) => c.path).slice(0, 3)).toEqual(['/voice/unlock', '/voice/unlock', '/voice/session'])
  })

  it('a host with no voice mode, and one that cannot check the code, each say so', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 })))
    let el = await mount()
    pick(el)
    await enter(el, 'DUSH26')
    expect($(el, '.vo-err').textContent).toBe('Voice mode is not available here')
    document.body.innerHTML = ''
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 503 })))
    el = await mount()
    pick(el)
    await enter(el, 'DUSH26')
    expect($(el, '.vo-err').textContent).toBe('Could not check the code. Try again.')
    expect($(el, '.vo-sheet').classList.contains('bad')).toBe(false)            // the code may be right
  })

  it('a conversation: what is heard is sent as a message, the orb thinks, speaks and listens; silent mode; leaving', async () => {
    const s = server(), audio = fakeAudio(), a = agent()
    const el = await talking(s, a)
    const session = s.calls.find((c) => c.path === '/voice/session')!
    expect(session.body).toEqual({ sdp: 'offer-sdp', thread_id: 'voice-1' })    // the chat's own thread
    expect(session.pass).toBe('pass-1')                                         // in a header, never in an address
    expect(audio.peers[0]).toMatchObject({ channel: 'oai-events', remote: 'answer-sdp' })
    expect(s.calls.some((c) => c.path === '/voice/events?talk=t1' && c.pass === 'pass-1')).toBe(true)
    const dock = $(el, '.vo-dock'), foot = $(el, '.foot')
    expect(foot.classList.contains('vo-on')).toBe(true)
    expect(dock.classList.contains('vo-listen')).toBe(true)
    // the person speaks: their message grows, then it is the ordinary message
    s.push({ type: 'hearing', delta: 'One and a half ' }); s.push({ type: 'hearing', delta: 'million' })
    await tick(10)
    expect($$(el, '.msg.me.vo-hearing').map((m) => m.textContent)).toEqual(['One and a half million'])
    s.push({ type: 'heard', text: 'One and a half million for four years', t_ms: 10 })
    await tick(10)
    expect($$(el, '.msg.me').map((m) => m.textContent)).toEqual(['One and a half million for four years'])   // one message, not two
    expect(dock.classList.contains('vo-think')).toBe(true)                      // the turn runs
    s.push({ type: 'spoken', delta: 'Checking now' })                          // the voice's own filler: a status under the orb, not a message
    await tick(10)
    expect($(el, '.vo-step').textContent).toBe('Checking now')
    await tick(80)
    expect(a.said).toEqual(['One and a half million for four years'])
    s.push({ type: 'result', text: 'Done.' }); s.push({ type: 'spoken', delta: 'Done' })
    await tick(10)
    expect($$(el, '.msg.ai').map((m) => m.textContent!.trim())).toEqual(['Done.'])   // the answer is one message: the written one
    expect(dock.classList.contains('vo-speak')).toBe(true)                      // the voice is talking
    await tick(1000)
    expect(dock.classList.contains('vo-listen')).toBe(true)
    // typing takes the row; the microphone stays within reach; it does not end voice
    const input = $<HTMLTextAreaElement>(el, 'textarea')
    input.value = 'for a car'; input.dispatchEvent(new Event('input'))
    expect(foot.classList.contains('vo-typing')).toBe(true)
    input.value = ''; input.dispatchEvent(new Event('input'))
    // silent mode: the microphone is released, the conversation with the voice ends, the chat goes on
    $(el, '.vo-mic').click()
    await tick(10)
    expect(dock.classList.contains('vo-silent')).toBe(true)
    expect(audio.open()).toBe(0)
    expect(audio.live.mics).toBe(0)
    expect(s.ends()).toEqual(['t1'])
    await el.send('typed in silence')
    await tick(80)
    expect(a.said.at(-1)).toBe('typed in silence')
    // the orb, pressed while silent, is the microphone too: voice is back
    $(el, '.vo-orb').click()
    await tick(30)
    expect(audio.open()).toBe(1)
    expect(dock.classList.contains('vo-listen')).toBe(true)
    // the close button leaves voice mode; the conversation stays
    $(el, '.vo-x').click()
    await tick(10)
    expect($(el, '.vo-dock')).toBeNull()
    expect(foot.classList.contains('vo-on')).toBe(false)
    expect($(el, '.vo-go').hidden).toBe(false)
    expect($$(el, '.msg.me')).toHaveLength(2)
    expect(audio.live.mics).toBe(0)
    expect(s.ends()).toEqual(['t1', 't2'])
  })

  it('the voice hearing itself through the speakers is not the person: its own sentence is never sent as their message', async () => {
    const s = server(); fakeAudio()
    const a = agent()
    const el = await talking(s, a)
    s.push({ type: 'heard', text: 'I want to book a table' })
    await tick(80)
    s.push({ type: 'result', text: 'Done.' })
    for (const d of ['Choose the date ', 'and time ', 'of the booking.']) s.push({ type: 'spoken', delta: d })   // the voice speaks its question
    await tick(10)
    // two seconds later the provider reports that very sentence as heard (the owner's case), and its growing text too
    s.push({ type: 'hearing', delta: 'Choose the date and time' })
    s.push({ type: 'heard', text: 'choose the date and time of the booking' })
    await tick(60)
    expect(a.said).toEqual(['I want to book a table'])                          // nothing was sent for the echo
    expect($$(el, '.msg.me').map((m) => m.textContent)).toEqual(['I want to book a table'])   // and no message of "his" stays
    // what the person really says next goes through, also a short answer that repeats the voice's words
    s.push({ type: 'heard', text: 'the fifth at seven in the evening' })
    await tick(80)
    s.push({ type: 'result', text: 'Done.' }); s.push({ type: 'spoken', delta: 'A car loan or a home loan?' })
    await tick(10)
    s.push({ type: 'heard', text: 'Car loan' })                                 // under four words: never taken for an echo
    await tick(80)
    expect(a.said).toEqual(['I want to book a table', 'the fifth at seven in the evening', 'Car loan'])
    // the browser is asked to cancel the echo in the first place
    const audio = vi.fn(async () => ({ getTracks: () => [{ stop() {} }] }))
    vi.stubGlobal('navigator', { ...navigator, mediaDevices: { getUserMedia: audio } })
    $(el, '.vo-mic').click(); await tick(10); $(el, '.vo-mic').click(); await tick(30)
    expect(audio).toHaveBeenCalledWith({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
  })

  it('small talk the agent is not asked about stays in the conversation: the words heard, and the voice\'s words as a message', async () => {
    const s = server(); fakeAudio()
    const el = await talking(s, agent())
    s.push({ type: 'hearing', delta: 'Hello there' })
    await tick(10)
    s.push({ type: 'spoken', delta: 'Hi! ' }); s.push({ type: 'spoken', delta: 'How can I help?' })
    await tick(10)
    expect($$(el, '.msg.me').map((m) => m.textContent)).toEqual(['Hello there'])
    expect($$(el, '.msg.me.vo-hearing')).toHaveLength(0)                        // it is said, no longer growing
    expect($$(el, '.msg.ai').map((m) => m.textContent)).toEqual(['Hi! How can I help?'])
  })

  it('a press on the orb stops the answer: the turn while it thinks, the sound while it speaks', async () => {
    const s = server(); fakeAudio()
    const a = agent(400)
    const el = await talking(s, a)
    s.push({ type: 'heard', text: 'What documents do I need?' })
    await tick(30)
    expect($(el, '.vo-dock').classList.contains('vo-think')).toBe(true)
    $(el, '.vo-orb').click()
    await tick(30)
    expect($(el, '.vo-dock').classList.contains('vo-think')).toBe(false)        // the turn was stopped
    expect($<HTMLAudioElement>(el, '.vo-dock audio').muted).toBe(true)          // and the voice is quiet
    s.push({ type: 'hearing', delta: 'And' })                                   // until the person speaks again
    await tick(10)
    expect($<HTMLAudioElement>(el, '.vo-dock audio').muted).toBe(false)
  })

  it('never leaves a microphone on without the orb: a tap during the permission prompt, a closed chat, a new chat', async () => {
    // the microphone button is tapped while the browser still asks for the microphone
    let allow!: () => void
    const s = server(), audio = fakeAudio(new Promise<void>((r) => { allow = r }))
    vi.stubGlobal('fetch', s.fetch)
    sessionStorage.setItem('agui-voice-pass', 'pass-1')
    let el = await mount()
    $(el, '.vo-go').click()
    await tick(10)
    $(el, '.vo-mic').click()                                                    // not after all
    allow()
    await tick(40)
    expect(audio.live.mics).toBe(0)                                             // the stream that arrived late was stopped
    expect(audio.open()).toBe(0)
    expect(s.calls.some((c) => c.path === '/voice/session')).toBe(false)
    expect($(el, '.vo-dock').classList.contains('vo-silent')).toBe(true)
    $(el, '.vo-mic').click()                                                    // and the button still works
    await tick(40)
    expect(audio.live.mics).toBe(1)
    expect($(el, '.vo-dock').classList.contains('vo-listen')).toBe(true)
    // the chat is closed (Esc, its close button, the scrim): the voice hangs up
    el.dispatchEvent(new CustomEvent('agui:close'))
    await tick(10)
    expect(audio.live.mics).toBe(0)
    expect(s.ends()).toEqual(['t1'])
    expect($(el, '.vo-dock').classList.contains('vo-silent')).toBe(true)
    // a new chat: the voice knew the old one
    $(el, '.vo-mic').click()
    await tick(40)
    el.dispatchEvent(new CustomEvent('agui:thread', { detail: 'other' }))
    await tick(10)
    expect(audio.live.mics).toBe(0)
    expect($$(el, '.notice').map((n) => n.textContent)).toEqual(['Voice mode stopped.'])
    // the chat leaves the page
    $(el, '.vo-mic').click()
    await tick(40)
    expect(audio.live.mics).toBe(1)
    el.remove()
    await tick(20)
    expect(audio.live.mics).toBe(0)
  })

  it('says why the voice ended or may not start, once, and falls back to silence', async () => {
    const s = server(); fakeAudio()
    let el = await talking(s)
    s.push({ type: 'ended', reason: 'time', cost_usd: 0.4 })
    await tick(20)
    expect($$(el, '.notice').map((n) => n.textContent)).toEqual(['Voice mode stopped: this conversation reached its limit. You can keep typing.'])
    expect($(el, '.vo-dock').classList.contains('vo-silent')).toBe(true)
    expect(s.ends()).toEqual([])                                                // the server ended it itself
    // it may not start: another conversation is going on; a second try does not pile the line up
    document.body.innerHTML = ''
    const busy = server({ session: () => new Response(JSON.stringify({ detail: { reason: 'busy' } }), { status: 429 }) })
    el = await talking(busy)
    $(el, '.vo-mic').click()
    await tick(30)
    expect($$(el, '.notice').map((n) => n.textContent)).toEqual(['Another voice conversation is going on. End it there, or try again in a minute.'])
    // the pass is no longer good: the code is asked again, with the reason
    document.body.innerHTML = ''
    const old = server({ session: () => new Response(null, { status: 403 }) })
    el = await talking(old)
    expect($(el, '.vo-err').textContent).toBe('Your code has expired. Enter it again.')
    expect(sessionStorage.getItem('agui-voice-pass')).toBeNull()
    expect($(el, '.vo-dock')).toBeNull()
  })

  it('fills quietly: a field-change card marked quiet is applied at once in voice mode, with no card to tap; without the mark, or out of voice, it waits', async () => {
    const { formguide } = await import('../src/formguide/index')
    const changes = [{ name: 'loan_amount', label: 'Amount', value: 1500000, display: '1 500 000', previous: null, previous_display: null, reveal: [] }]
    const card = (id: string, quiet: boolean) => ({ type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'set_fields', card_id: id, changes, ...(quiet ? { quiet: true } : {}) }) })
    const s = server(); fakeAudio()
    vi.stubGlobal('fetch', s.fetch)
    sessionStorage.setItem('agui-voice-pass', 'pass-1')
    const el = await mount()
    const applied: unknown[] = [], resumed: unknown[] = []
    el.use(formguide({ getState: () => ({ config: { state: {}, props: {} }, jsx_hash: 'h', form_id: 'loan', ui: { focused: null } }), applyChanges: async (c: Record<string, unknown>) => { applied.push(c); return { state: c } } }))
    const turns = [[card('c1', true)], [], [card('c2', false)], [card('c3', true)]]
    el.agent = { run: (input: { forwardedProps?: { command?: { resume?: unknown } } }) => ({ subscribe: (o: Obs) => {
      if (input.forwardedProps?.command?.resume) resumed.push(input.forwardedProps.command.resume)
      const evs = input.forwardedProps?.command?.resume ? [] : turns.shift() ?? []
      setTimeout(() => { o.next({ type: 'RUN_STARTED' }); for (const e of evs) o.next(e); o.next({ type: 'RUN_FINISHED' }); o.complete() }, 10)
      return { unsubscribe() {} } } }) } as never
    $(el, '.vo-go').click()
    await tick(30)
    s.push({ type: 'heard', text: 'One and a half million' })
    await tick(120)
    expect(applied).toEqual([{ loan_amount: 1500000 }])                         // filled through the host's form, with no tap
    expect(resumed).toHaveLength(1)
    expect(resumed[0]).toMatchObject({ accepted: true })                        // the same answer an accepted card gives
    expect($$(el, '.card .btn.pri')).toHaveLength(0)                            // no card waiting
    expect($(el, '[data-card-id="c1"] .ok-line')).not.toBeNull()                // its result line, with Undo, is in the conversation
    s.push({ type: 'heard', text: 'and the term?' })                            // (a turn with nothing to fill)
    await tick(60)
    s.push({ type: 'heard', text: 'change my name to Anna' })                   // not marked quiet: a card that waits, as in chat
    await tick(120)
    expect($$(el, '[data-card-id="c2"] .btn.pri')).toHaveLength(1)
    expect(applied).toHaveLength(1)
    ;($(el, '[data-card-id="c2"] .btn.pri') as HTMLButtonElement).click()
    await tick(60)
    $(el, '.vo-x').click()                                                      // voice mode left: a quiet mark means nothing in the plain chat
    await el.send('amount again')
    await tick(120)
    expect($$(el, '[data-card-id="c3"] .btn.pri')).toHaveLength(1)
  })

  it('speaks the chat\'s language', async () => {
    vi.stubGlobal('fetch', server().fetch)
    const el = await mount({ lang: 'de' })
    for (let i = 0; i < 50 && el.lang !== 'de'; i++) await tick(10)
    pick(el)
    expect($(el, '.vo-sheet button[type=submit]').textContent).toBe('Experimentellen Modus aktivieren')
    expect($(el, '.vo-sheet b').textContent).toBe('Experimenteller Sprachmodus')
  })
})

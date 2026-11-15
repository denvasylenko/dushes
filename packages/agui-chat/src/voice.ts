/**
 * The experimental voice mode: talk to the chat instead of typing. The chat stays as it is; an orb sits above the
 * input, the person's spoken words arrive as their message, and the agent's answer is the chat's own answer, spoken
 * by the voice. It is off unless the host turns it on (`voice-mode` on the element; `voice` is the dictation option)
 * and the person has entered their code.
 *
 *   - "+" menu -> "Experimental voice mode" -> a sheet for the code -> voice starts; later a small orb in the message
 *     box starts it in one tap.
 *   - A conversation: the microphone, a WebRTC connection to the host's voice endpoint, and its event stream.
 *     `hearing` grows the person's message as they speak, `heard` sends it as an ordinary message; the voice's own
 *     words with no agent answer behind them are an assistant message; an answer is one message, the written one.
 *   - The orb: listening (turning), thinking (smaller, lifted, faster, with the turn's step under it), speaking,
 *     silent (grey, still). A press stops the answer being thought or spoken; while listening it turns the
 *     microphone off, while silent it turns it on.
 *   - The microphone button is silent mode: the conversation with the voice ends and the microphone is released, the
 *     chat goes on in text; the same button starts the voice again. The close button leaves voice mode.
 *   - The microphone is never on without the moving orb on screen: closing the chat, leaving the page, a new chat or
 *     a failed start all end the conversation with the voice.
 *
 * It uses only the element's public surface (options, send, stop, threadId, events) and its open shadow root, and
 * loads as its own file (agui-chat.voice.js) when the host has turned voice mode on. No key reaches the browser: the
 * host's endpoint answers the WebRTC offer.
 */
import { VOICE_CSS } from './voice-css'
import { VOICE_STRINGS } from './voice-strings'

interface Chat extends HTMLElement {
  options: Record<string, unknown> & { menu?: { id: string; label: string; hint?: string; icon?: string }[]; url?: string; i18n?: Record<string, string>; voiceUrl?: string }
  lang: string; threadId: string
  send(text: string): Promise<void>; stop(): void
}
type Ended = 'closed' | 'time' | 'money' | 'silence' | 'day' | 'lost' | 'busy' | 'person_day'

const MIC = 'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3M6 11.5a6 6 0 0 0 12 0M12 17.5V21'
const svg = (d: string, size = 20): string => `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`
const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, text?: string): HTMLElementTagNameMap[K] => {
  const e = document.createElement(tag); if (cls) e.className = cls
  if (text !== undefined) e.textContent = text
  return e
}
const KEY = 'agui-voice-pass'
const store = { get: (): string => { try { return sessionStorage.getItem(KEY) ?? '' } catch { return '' } },
  set: (v: string): void => { try { if (v) sessionStorage.setItem(KEY, v); else sessionStorage.removeItem(KEY) } catch { /* a private window: kept for this page only */ } } }

const done = new WeakSet<HTMLElement>()

/** Turn voice mode on for a chat element. Safe to call twice. */
export function voice(chat: Chat): void {
  const root = chat.shadowRoot
  if (!root || done.has(chat)) return
  done.add(chat)
  try { const sh = new CSSStyleSheet(); sh.replaceSync(VOICE_CSS); root.adoptedStyleSheets = [...root.adoptedStyleSheets, sh] }
  catch { const st = document.createElement('style'); st.textContent = VOICE_CSS; root.append(st) }
  const $ = <T extends HTMLElement>(s: string): T => root.querySelector<T>(s)!
  const panel = $('.panel'), foot = $('.foot'), box = $('.box'), input = $<HTMLTextAreaElement>('.box textarea')
  const T = (k: string): string => chat.options.i18n?.[`voice${k[0].toUpperCase()}${k.slice(1)}`] ?? VOICE_STRINGS[chat.lang]?.[k] ?? VOICE_STRINGS.en[k] ?? k
  const base = (): string => (chat.getAttribute('voice-url') || chat.options.voiceUrl || new URL('/voice', new URL(chat.options.url || '/', location.href)).href).replace(/\/$/, '')
  const call = (path: string, body: unknown, pass = ''): Promise<Response> => fetch(`${base()}${path}`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(pass ? { 'X-Voice-Pass': pass } : {}) }, body: JSON.stringify(body) })

  let pass = store.get()
  // ------------------------------------------------------------------ the way in: a row in the + menu, then the code
  const row = (): void => { chat.options = { menu: [...(chat.options.menu ?? []).filter((m) => m.id !== 'agui-voice'), { id: 'agui-voice', label: T('menu'), hint: pass ? undefined : T('needsCode'), icon: MIC }] } }
  row()
  chat.addEventListener('agui:menu-action', (e) => {
    if ((e as CustomEvent).detail?.id !== 'agui-voice') return
    e.preventDefault()
    if (pass) void start(); else sheet()
  })
  /** The small orb in the message box, where the microphone was: one tap starts voice. */
  const go = el('button', 'vo-go'); go.type = 'button'; go.append(el('i', '')); go.hidden = true
  go.addEventListener('click', () => void start())
  box.querySelector('.send')!.before(go)
  const ready = (): void => { go.hidden = !pass; foot.classList.toggle('vo-ready', !!pass); go.setAttribute('aria-label', T('start')); go.title = T('start'); row() }
  ready()

  /** The code. `reason`: why it is asked again (the pass ran out). */
  function sheet(reason = ''): void {
    if (root!.querySelector('.vo-sheet')) return
    const veil = el('div', 'vo-veil'), s = el('form', 'vo-sheet')
    s.setAttribute('role', 'dialog'); s.setAttribute('aria-modal', 'true'); s.setAttribute('aria-label', T('menu'))
    const code = el('input', ''); code.type = 'text'; code.autocomplete = 'off'; code.autocapitalize = 'characters'; code.spellcheck = false
    code.setAttribute('aria-label', T('codeLabel')); code.placeholder = T('codeLabel')
    const err = el('div', 'vo-err', reason); err.setAttribute('role', 'alert')
    const ok = el('button', '', T('activate')); ok.type = 'submit'; ok.disabled = true
    const no = el('button', 'q', T('notNow')); no.type = 'button'
    s.append(el('b', '', T('menu')), el('p', '', T('intro')), code, err, ok, no)
    const shut = (focus = true): void => { document.removeEventListener('keydown', key, true); veil.remove(); s.remove(); if (focus) $<HTMLElement>('.box .clip')?.focus({ preventScroll: true }) }
    const key = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); shut(); return }
      if (e.key !== 'Tab') return   // the sheet holds the focus while it is open
      const f = [code, ok, no].filter((x) => !(x as HTMLButtonElement).disabled), cur = root!.activeElement, last = f[f.length - 1]
      if (!s.contains(cur) || (e.shiftKey ? cur === f[0] : cur === last)) { e.preventDefault(); (e.shiftKey ? last : f[0]).focus() }
    }
    code.addEventListener('input', () => { ok.disabled = !code.value.trim(); s.classList.remove('bad'); code.removeAttribute('aria-invalid'); err.textContent = '' })
    no.addEventListener('click', () => shut()); veil.addEventListener('click', () => shut())
    s.addEventListener('submit', async (e) => {
      e.preventDefault()
      if (ok.disabled) return
      ok.disabled = true; s.classList.add('busy')
      let r: Response | null = null
      try { r = await call('/unlock', { code: code.value.trim() }) } catch { /* no connection */ }
      s.classList.remove('busy')
      if (r?.ok) { pass = String((await r.json()).pass ?? ''); store.set(pass); shut(false); ready(); void start(); return }   // they asked for voice: it starts
      err.textContent = T(!r ? 'noConnect' : r.status === 404 ? 'noVoice' : r.status === 403 ? 'badCode' : 'noCheck')
      if (r?.status === 403) { s.classList.add('bad'); code.setAttribute('aria-invalid', 'true'); code.select() }
      ok.disabled = !code.value.trim()
    })
    document.addEventListener('keydown', key, true)
    panel.append(veil, s)
    code.focus({ preventScroll: true })
  }

  // ------------------------------------------------------------------ the conversation
  let pc: RTCPeerConnection | null = null, mic: MediaStream | null = null, talk = '', reader: ReadableStreamDefaultReader<Uint8Array> | null = null
  let on = false, silent = false, busy = false, spokeAt = 0, wait = false, gen = 0
  const dock = el('div', 'vo-dock'), orb = el('button', 'vo-orb'), step = el('div', 'vo-step'), audio = el('audio', '')
  orb.type = 'button'; orb.innerHTML = svg('M8 8h8v8H8z', 22); step.setAttribute('role', 'status'); audio.autoplay = true
  dock.append(orb, step, audio)
  const bMic = el('button', 'vo-b vo-mic'), bX = el('button', 'vo-b vo-x')
  bMic.type = 'button'; bX.type = 'button'; bX.innerHTML = svg('M6.5 6.5l11 11m0-11-11 11', 18)

  /** What the orb shows: silent, or waiting for the connection, or thinking (a turn runs), speaking, listening. */
  function paint(): void {
    const speaking = !silent && !audio.muted && Date.now() - spokeAt < 900
    const state = silent ? 'silent' : wait ? 'wait' : busy ? 'think' : speaking ? 'speak' : 'listen'
    for (const s of ['silent', 'wait', 'think', 'speak', 'listen']) dock.classList.toggle(`vo-${s}`, s === state)
    orb.setAttribute('aria-label', T(state === 'think' || state === 'speak' ? 'stop' : silent ? 'micOn' : wait ? 'connecting' : 'micOff'))
    if (wait) step.textContent = T('connecting'); else if (!busy && !caption) step.textContent = silent ? '' : state === 'listen' ? T('listening') : step.textContent
    bMic.innerHTML = svg(silent ? `${MIC}M4 3l16 18` : MIC); bMic.classList.toggle('on', silent)
    bMic.setAttribute('aria-label', T(silent ? 'micOn' : 'micOff')); bMic.title = T(silent ? 'micOn' : 'micOff')
    bX.setAttribute('aria-label', T('end')); bX.title = T('end')
  }
  const typing = (): void => { foot.classList.toggle('vo-typing', on && (!!input.value || root.activeElement === input)) }
  input.addEventListener('input', typing); input.addEventListener('focus', typing); input.addEventListener('blur', () => setTimeout(typing, 0))
  // a turn runs while the element says `busy` (it ends that on a finished, a stopped and a failed turn alike)
  new MutationObserver(() => { busy = chat.hasAttribute('busy'); caption = ''; if (!busy) step.textContent = ''; paint(); if (!busy) setTimeout(typing, 0) }).observe(chat, { attributes: true, attributeFilter: ['busy'] })
  // the turn's own step, under the orb while it works (the conversation's own live line is hidden meanwhile)
  chat.addEventListener('agui:event', (e) => {
    if (!on || (e as CustomEvent).detail?.type !== 'TOOL_CALL_START') return
    queueMicrotask(() => { const all = root.querySelectorAll('.log .steps-t'); caption = ''; step.textContent = all[all.length - 1]?.textContent ?? '' })
  })
  // the orb always does something: it stops the answer being thought or spoken; otherwise it is the microphone
  orb.addEventListener('click', () => {
    if (busy) { chat.stop(); audio.muted = true; paint(); return }
    if (!silent && Date.now() - spokeAt < 900) { audio.muted = true; paint(); return }   // quiet until the person speaks again
    toggle()
  })
  const toggle = (): void => { if (silent) void connect(); else { hang(true); silent = true; paint() } }   // also while it connects: the microphone is not wanted after all
  bMic.addEventListener('click', toggle)
  bX.addEventListener('click', () => leave())
  // never a live microphone without the orb on screen
  chat.addEventListener('agui:close', () => { if (on && !silent) { hang(true); silent = true; paint() } })
  chat.addEventListener('agui:thread', () => { if (on && !silent) fail(T('closed')) })   // a new chat: the voice knew the old one
  globalThis.addEventListener?.('pagehide', () => { if (on) hang(true, true) })
  new MutationObserver(() => { if (on && !chat.isConnected) leave() }).observe(document, { childList: true, subtree: true })

  /** Everything said and heard goes into the conversation itself, never into a strip of its own. */
  const add = (e: HTMLElement): void => (chat as unknown as { append(e: HTMLElement): void }).append(e)
  let last: HTMLElement | null = null
  /** One line that says why voice ended; a new one takes the place of the last, they never pile up. */
  function note(text: string): void { last?.remove(); last = el('div', 'notice', text); add(last) }
  let hearEl: HTMLElement | null = null, saidEl: HTMLElement | null = null, answered = false, caption = ''
  /** How loud the voice is, from the sound itself (frames arrive all the time, silence included): it is speaking while there is sound. */
  let ear: { ctx: AudioContext; timer: ReturnType<typeof setInterval> } | null = null
  function listenTo(stream: MediaStream): void {
    const AC = (globalThis as unknown as { AudioContext?: typeof AudioContext }).AudioContext
    if (!AC || ear) return
    try {
      const ctx = new AC(), an = ctx.createAnalyser(), data = new Uint8Array(256)
      an.fftSize = 256; ctx.createMediaStreamSource(stream).connect(an)
      ear = { ctx, timer: setInterval(() => {
        an.getByteTimeDomainData(data)
        let sum = 0
        for (const v of data) sum += (v - 128) * (v - 128)
        if (Math.sqrt(sum / data.length) > 4) { const was = Date.now() - spokeAt < 900; spokeAt = Date.now(); if (!was) paint() } else if (dock.classList.contains('vo-speak') && Date.now() - spokeAt >= 900) paint()
      }, 120) }
    } catch { /* no audio graph here: the transcript events show speaking instead */ }
  }

  /** Enter voice mode and connect. */
  async function start(): Promise<void> {
    if (on) return
    on = true; silent = false
    foot.classList.add('vo-on'); box.before(dock); box.after(bMic, bX)
    typing()
    if (root!.activeElement !== input) bMic.focus({ preventScroll: true })
    await connect()
  }
  /** Connect to the voice. Every step checks it is still wanted: a tap on the microphone or the close button while
   *  the browser asks for the microphone must leave nothing running. */
  async function connect(): Promise<void> {
    if (pc || wait) return
    const mine = ++gen
    const stale = (): boolean => mine !== gen || !on || silent
    wait = true; silent = false; audio.muted = false; paint()
    let stream: MediaStream | null = null, p: RTCPeerConnection | null = null, id = ''
    const drop = (): void => { stream?.getTracks().forEach((t) => t.stop()); p?.close(); if (id) void call('/end', { talk: id }, pass).catch(() => {}) }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      if (stale()) return drop()
      p = new RTCPeerConnection()
      p.ontrack = (e) => { if (pc === p) { audio.srcObject = e.streams[0]; listenTo(e.streams[0]) } }
      for (const t of stream.getTracks()) p.addTrack(t, stream)
      p.createDataChannel('oai-events')
      await p.setLocalDescription(await p.createOffer())
      if (stale()) return drop()
      const r = await call('/session', { sdp: p.localDescription!.sdp, thread_id: chat.threadId }, pass)
      if (stale()) { if (r.ok) id = String(((await r.json().catch(() => ({}))) as { talk?: string }).talk ?? ''); return drop() }
      if (r.status === 403) { drop(); pass = ''; store.set(''); leave(false); ready(); sheet(T('expired')); return }
      if (!r.ok) { drop(); const d = await r.json().catch(() => ({})) as { detail?: { reason?: Ended } }; fail(d.detail?.reason ? why(d.detail.reason) : T('unavailable')); return }
      const got = await r.json() as { talk: string; sdp: string }
      id = got.talk
      await p.setRemoteDescription({ type: 'answer', sdp: got.sdp })
      if (stale()) return drop()
      pc = p; mic = stream; talk = id; wait = false; last?.remove(); last = null; paint()
      void follow(p)
    } catch (e) {
      drop()
      if (mine === gen) fail(T((e as Error)?.name === 'NotAllowedError' ? 'noMic' : 'noConnect'))
    }
  }
  const why = (r: Ended): string => T(({ time: 'limit', money: 'limit', silence: 'silence', day: 'day', busy: 'busy', person_day: 'personDay', lost: 'lost', closed: 'closed' } as Record<string, string>)[r] ?? 'closed')
  /** The voice could not start or was cut: say why in the conversation; the chat goes on in text (silent). */
  function fail(text: string): void { hang(false); silent = true; paint(); note(text) }

  async function follow(p: RTCPeerConnection): Promise<void> {
    let r: Response
    try { r = await fetch(`${base()}/events?talk=${encodeURIComponent(talk)}`, { headers: { 'X-Voice-Pass': pass } }) } catch { if (pc === p) fail(why('lost')); return }
    if (!r.body || pc !== p) return
    const rd = reader = r.body.getReader(), dec = new TextDecoder()
    let buf = ''
    for (;;) {
      const { value, done: end } = await rd.read().catch(() => ({ value: undefined, done: true }))
      if (end || pc !== p) break
      buf += dec.decode(value, { stream: true })
      let cut: number
      while ((cut = buf.search(/\r?\n\r?\n/)) >= 0) {
        const block = buf.slice(0, cut); buf = buf.slice(cut).replace(/^\r?\n\r?\n/, '')
        const data = block.split(/\r?\n/).filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('')
        if (!data) continue
        let ev: { type?: string; text?: string; delta?: string; reason?: Ended }
        try { ev = JSON.parse(data) } catch { continue }
        if (ev.type === 'hearing' && ev.delta) {   // the person's words as they speak: their message, growing in the conversation
          audio.muted = false
          if (!hearEl) { hearEl = el('div', 'msg me vo-hearing'); hearEl.append(el('div', 'bubble')); add(hearEl); saidEl = null; answered = false }
          hearEl.firstElementChild!.textContent += ev.delta
        } else if (ev.type === 'heard' && ev.text) {   // the whole request: the ordinary turn, as if typed; its text, steps and cards are the chat's own
          audio.muted = false
          hearEl?.remove(); hearEl = null; saidEl = null; answered = false
          void chat.send(ev.text)
        } else if (ev.type === 'result') { answered = true; saidEl = null   // the agent's answer was handed to the voice: what it says next is that answer, already written in the conversation
        } else if (ev.type === 'spoken' && ev.delta) {
          spokeAt = Date.now(); paint(); setTimeout(paint, 950)
          if (answered) continue   // one message for one answer: the written one
          if (busy) { caption = (caption + ev.delta).slice(-80); step.textContent = caption; continue }   // "Checking now": a status, under the orb
          // the voice's own words with no agent answer behind them (a greeting, small talk): the agent's message, word by word
          if (hearEl) { hearEl.classList.remove('vo-hearing'); hearEl = null }
          if (!saidEl) { saidEl = el('div', 'msg ai'); saidEl.append(el('div', 'body')); add(saidEl) }
          saidEl.firstElementChild!.textContent += ev.delta
        } else if (ev.type === 'ended') {
          const reason = ev.reason ?? 'closed'
          hang(false); silent = true; paint()
          if (reason !== 'closed') note(why(reason))
          return
        }
      }
    }
    if (pc === p) fail(why('lost'))
  }
  /** End the conversation with the voice and release the microphone (the chat itself goes on). `tell`: the server has
   *  not ended it itself; `leaving`: the page is going away, so the call must outlive it. */
  function hang(tell: boolean, leaving = false): void {
    gen++   // a connection still being made is no longer wanted
    try { void reader?.cancel() } catch { /* already closed */ }
    if (talk && tell) { try { void fetch(`${base()}/end`, { method: 'POST', keepalive: leaving, headers: { 'Content-Type': 'application/json', 'X-Voice-Pass': pass }, body: JSON.stringify({ talk }) }).catch(() => {}) } catch { /* leaving anyway */ } }
    pc?.close(); mic?.getTracks().forEach((t) => t.stop())
    pc = null; mic = null; reader = null; talk = ''; wait = false; audio.srcObject = null; audio.muted = false
    if (ear) { clearInterval(ear.timer); void ear.ctx.close().catch(() => {}); ear = null }
    hearEl?.classList.remove('vo-hearing'); hearEl = null; saidEl = null; caption = ''; step.textContent = ''
  }
  /** Leave voice mode: the conversation above is untouched, the small orb is back in the message box. */
  function leave(focus = true): void {
    if (!on) return
    hang(true)
    on = false; silent = false
    dock.remove(); bMic.remove(); bX.remove(); foot.classList.remove('vo-on', 'vo-typing')
    if (focus && chat.isConnected) go.focus({ preventScroll: true })
  }
}

// the one-script build: agui-chat.voice.js registers it on window.AguiChat
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.voice = voice

/** Dictation with the browser's speech recognition (Chrome, Edge, Safari). Text goes into the composer. */

interface Recognition {
  lang: string; continuous: boolean; interimResults: boolean
  onresult: ((e: { resultIndex: number; results: { length: number; [i: number]: { isFinal: boolean; 0: { transcript: string } } } }) => void) | null
  onerror: ((e: { error: string }) => void) | null
  onend: (() => void) | null
  start(): void; stop(): void; abort(): void
}

export const speechSupported = (): boolean =>
  typeof window !== 'undefined' && !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) // eslint-disable-line @typescript-eslint/no-explicit-any

export interface Dictation {
  /** Stop listening; the last words may still arrive (a final result). */
  stop(): void
  /** Stop at once and drop anything not delivered yet (used when the message is sent). */
  abort(): void
}

/** Start dictating; `onText(full)` gets the text so far (finals + the current guess). */
export function dictate(lang: string, onText: (text: string) => void, onState: (on: boolean, error?: string) => void): Dictation {
  const R = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition // eslint-disable-line @typescript-eslint/no-explicit-any
  const r: Recognition = new R()
  r.lang = lang
  r.continuous = true
  r.interimResults = true
  let finals = ''
  let dead = false
  r.onresult = (e) => {
    if (dead) return
    let guess = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const res = e.results[i]
      if (res.isFinal) finals += res[0].transcript
      else guess += res[0].transcript
    }
    onText((finals + guess).trim())
  }
  r.onerror = (e) => { if (e.error !== 'aborted') onState(false, e.error === 'not-allowed' || e.error === 'service-not-allowed' ? 'denied' : e.error) }
  r.onend = () => onState(false)
  r.start()
  onState(true)
  return {
    stop: () => { try { r.stop() } catch { /* already stopped */ } },
    abort: () => { dead = true; try { r.abort() } catch { /* already stopped */ } onState(false) },
  }
}

// ------------------------------------------------------------------ dictation on the server (a recording)

/** The browser can record audio for server-side transcription. */
export const recordingSupported = (): boolean =>
  typeof window !== 'undefined' && typeof (window as any).MediaRecorder === 'function' && !!navigator.mediaDevices?.getUserMedia // eslint-disable-line @typescript-eslint/no-explicit-any

/** Errors of the browser's recognition after which a recording for the server is worth a try (the service is
 * blocked or unreachable, not the microphone). */
export const recognitionBlocked = (error?: string): boolean =>
  !!error && ['network', 'service-not-allowed', 'language-not-supported', 'not-supported'].includes(error)

export interface RecordingHooks {
  /** The voice level, 0..1, about 12 times a second. */
  level(v: number): void
  /** 'rec' while recording, 'busy' while the server transcribes, 'off' when done (with an error code). */
  state(s: 'rec' | 'busy' | 'off', error?: 'denied' | 'empty' | 'failed' | 'unavailable'): void
  /** The recognised text. */
  text(t: string): void
  /** Post the recording, resolve with the text. */
  transcribe(audio: Blob): Promise<string>
}

/** Record until stop(), then transcribe on the server; abort() drops the recording. */
export function record(hooks: RecordingHooks, maxMs = 120_000): Dictation & { retry(): void } {
  let dead = false
  let stream: MediaStream | null = null
  let rec: MediaRecorder | null = null
  let ctx: AudioContext | null = null
  let timer = 0
  let cut = 0
  let last: Blob | null = null
  const chunks: Blob[] = []

  const release = () => {
    window.clearInterval(timer); window.clearTimeout(cut)
    stream?.getTracks().forEach((t) => t.stop())
    void ctx?.close().catch(() => {})
    stream = null; ctx = null
  }
  const send = async (audio: Blob) => {
    last = audio
    hooks.state('busy')
    try {
      const text = (await hooks.transcribe(audio)).trim()
      if (dead) return
      if (text) hooks.text(text)
      hooks.state('off', text ? undefined : 'empty')
    } catch (e) {
      if (!dead) hooks.state('off', (e as { status?: number })?.status === 501 ? 'unavailable' : 'failed')
    }
  }

  void (async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    } catch {
      if (!dead) hooks.state('off', 'denied')
      return
    }
    if (dead) { release(); return }
    const type = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'].find((t) => MediaRecorder.isTypeSupported?.(t))
    rec = new MediaRecorder(stream, type ? { mimeType: type } : undefined)
    rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
    rec.onstop = () => {
      release()
      if (dead) return
      void send(new Blob(chunks, { type: rec?.mimeType || type || 'audio/webm' }))
    }
    // the level meter for the wave: RMS of the signal, eased
    try {
      ctx = new AudioContext()
      const an = ctx.createAnalyser()
      an.fftSize = 512
      ctx.createMediaStreamSource(stream).connect(an)
      const buf = new Uint8Array(an.fftSize)
      let eased = 0
      timer = window.setInterval(() => {
        an.getByteTimeDomainData(buf)
        let sum = 0
        for (const b of buf) sum += ((b - 128) / 128) ** 2
        eased = eased * 0.4 + Math.min(1, Math.sqrt(sum / buf.length) * 4) * 0.6
        hooks.level(eased)
      }, 80)
    } catch { /* no meter: the wave stays flat, the recording works */ }
    rec.start(250)
    hooks.state('rec')
    cut = window.setTimeout(() => { if (rec?.state === 'recording') rec.stop() }, maxMs)   // too long: stop and transcribe
  })()

  return {
    stop: () => { if (rec?.state === 'recording') rec.stop() },
    abort: () => {
      dead = true
      try { if (rec?.state === 'recording') rec.stop() } catch { /* stopped */ }
      release()
      hooks.state('off')
    },
    retry: () => { if (last && !dead) void send(last) },
  }
}

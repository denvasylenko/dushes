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

/** Start dictating; `onText(full)` gets the text so far (finals + the current guess). Returns stop(). */
export function dictate(lang: string, onText: (text: string) => void, onState: (on: boolean, error?: string) => void): () => void {
  const R = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition // eslint-disable-line @typescript-eslint/no-explicit-any
  const r: Recognition = new R()
  r.lang = lang
  r.continuous = true
  r.interimResults = true
  let finals = ''
  r.onresult = (e) => {
    let guess = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const res = e.results[i]
      if (res.isFinal) finals += res[0].transcript
      else guess += res[0].transcript
    }
    onText((finals + guess).trim())
  }
  r.onerror = (e) => onState(false, e.error === 'not-allowed' || e.error === 'service-not-allowed' ? 'denied' : e.error)
  r.onend = () => onState(false)
  r.start()
  onState(true)
  return () => { try { r.stop() } catch { /* already stopped */ } }
}

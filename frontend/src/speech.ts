import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Voice input for the demo chat through the browser's Web Speech API (Chrome, Edge, Safari).
 * No backend involved; note that Chrome sends the audio to its own speech service.
 */

// Minimal typing: the Web Speech API is not in TypeScript's DOM library.
type Recognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  start(): void
  stop(): void
  abort(): void
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null
  onerror: ((e: { error: string }) => void) | null
  onend: (() => void) | null
}

function recognitionClass(): (new () => Recognition) | null {
  const w = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

/** Languages offered in the picker; "" = the browser's language. */
export const SPEECH_LANGS = ['', 'en-US', 'ru-RU', 'uk-UA', 'de-DE', 'fr-FR', 'es-ES', 'it-IT', 'pl-PL']

/**
 * `onText(text, final)` gets the text recognised so far in this session (interim while speaking).
 * The session stops on silence or when `stop()` is called.
 */
export function useSpeech(lang: string, onText: (text: string, final: boolean) => void) {
  const supported = recognitionClass() !== null
  const [listening, setListening] = useState(false)
  const [error, setError] = useState('')
  const rec = useRef<Recognition | null>(null)
  const cb = useRef(onText)
  cb.current = onText

  const stop = useCallback(() => rec.current?.stop(), [])
  /** Stop at once and drop anything still being recognised (used when the message is sent). */
  const cancel = useCallback(() => {
    const r = rec.current
    if (!r) return
    r.onresult = null
    r.abort()
    rec.current = null
    setListening(false)
  }, [])

  const start = useCallback(() => {
    const Cls = recognitionClass()
    if (!Cls || rec.current) return
    const r = new Cls()
    r.lang = lang || navigator.language
    r.continuous = true
    r.interimResults = true
    let finalText = ''
    r.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i]
        if (res.isFinal) finalText += res[0].transcript
        else interim += res[0].transcript
      }
      cb.current((finalText + interim).trim(), !interim)
    }
    r.onerror = (e) => setError(e.error === 'not-allowed' ? 'Microphone access was denied' : `Speech: ${e.error}`)
    r.onend = () => {
      rec.current = null
      setListening(false)
    }
    setError('')
    rec.current = r
    r.start()
    setListening(true)
  }, [lang])

  useEffect(() => () => rec.current?.stop(), [])
  return { supported, listening, error, start, stop, cancel }
}

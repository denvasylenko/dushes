/** A scripted AG-UI agent for the widget's browser tests: each /agent/run answers with the next scripted run. */
import type { Page, Route } from '@playwright/test'

export type Event = Record<string, unknown>

export const text = (id: string, s: string): Event[] => [
  { type: 'TEXT_MESSAGE_START', messageId: id, role: 'assistant' },
  { type: 'TEXT_MESSAGE_CONTENT', messageId: id, delta: s },
  { type: 'TEXT_MESSAGE_END', messageId: id },
]
export const suggestions = (...items: string[]): Event => ({ type: 'CUSTOM', name: 'suggestions', value: { items } })
export const run = (...body: Event[]): Event[] =>
  [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, ...body, { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]

export interface Script { delayMs?: number; events: Event[] }

/** Answers /agent/run with the scripts in order (the last one repeats); returns the request bodies it got. */
export async function agent(page: Page, ...scripts: Script[]): Promise<Record<string, unknown>[]> {
  const bodies: Record<string, unknown>[] = []
  let i = 0
  await page.route('**/agent/run', async (route: Route) => {
    bodies.push(JSON.parse(route.request().postData() || '{}'))
    const s = scripts[Math.min(i++, scripts.length - 1)]
    if (s.delayMs) await new Promise((r) => setTimeout(r, s.delayMs))
    await route.fulfill({ status: 200, contentType: 'text/event-stream',
                          body: s.events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('') }).catch(() => {})
  })
  return bodies
}

/** A microphone that works in every engine: getUserMedia gives a silent tone from Web Audio. */
export async function fakeMic(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const md = navigator.mediaDevices || ((navigator as unknown as { mediaDevices: object }).mediaDevices = {} as MediaDevices)
    ;(md as MediaDevices).getUserMedia = async () => {
      const ctx = new AudioContext()
      const osc = ctx.createOscillator()
      const dst = ctx.createMediaStreamDestination()
      osc.connect(dst); osc.start()
      return dst.stream
    }
  })
}

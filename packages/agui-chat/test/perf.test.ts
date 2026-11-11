/**
 * Speed budgets for the widget (happy-dom). The fastest of several runs is compared with a budget about
 * ten times the number measured on a laptop (Apple M-series): 5,000 SSE events 4.6 ms, one typewriter
 * frame on a 3,500-character answer 5.7 ms, 200 messages 12 ms. Only a real slowdown fails.
 * PERF_PRINT=1 npx vitest run test/perf.test.ts prints the numbers.
 */
import { describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { sseEvents } from '../src/transport'
import { fadeWords, newState, step, visible } from '../src/typewriter'
import { md } from '../src/dom'

function fastest(fn: () => void | Promise<void>, runs = 5): Promise<number> {
  return (async () => {
    await fn()
    let best = Infinity
    for (let i = 0; i < runs; i++) {
      const t = performance.now()
      await fn()
      best = Math.min(best, performance.now() - t)
    }
    return best
  })()
}

function within(name: string, ms: number, budget: number): void {
  if (process.env.PERF_PRINT) console.log(`${name}: ${ms.toFixed(2)} ms (budget ${budget} ms)`)
  expect(ms, `${name}: ${ms.toFixed(1)} ms, budget ${budget} ms`).toBeLessThanOrEqual(budget)
}

describe('speed', () => {
  it('parses 5,000 SSE events quickly', async () => {
    const one = (i: number) => `data: ${JSON.stringify({ type: 'TEXT_MESSAGE_CONTENT', messageId: 'm', delta: `word ${i} ` })}\n\n`
    const text = Array.from({ length: 5000 }, (_, i) => one(i)).join('')
    const bytes = new TextEncoder().encode(text)
    const ms = await fastest(async () => {
      const body = new ReadableStream<Uint8Array>({ start(c) { for (let i = 0; i < bytes.length; i += 4096) c.enqueue(bytes.slice(i, i + 4096)); c.close() } })
      let n = 0
      for await (const _ of sseEvents(body)) n++
      expect(n).toBe(5000)
    })
    within('5,000 SSE events', ms, 60)
  })

  it('keeps a typewriter frame cheap on a long answer', async () => {
    const answer = ('The **Loan** tab opens next. You need your passport, a payslip and the car details. ').repeat(40)
    const box = document.createElement('div')
    document.body.appendChild(box)
    const st = newState(answer.length - 200)
    let now = 1000
    const ms = await fastest(() => {
      now += 16
      step(st, answer, now)
      box.innerHTML = md(visible(answer, st.shown))
      fadeWords(box, st, now)
    }, 20)
    within('one typewriter frame', ms, 60)
  })

  it('renders 200 messages without a jank', async () => {
    vi.stubGlobal('fetch', vi.fn())
    const el = document.createElement('agui-chat') as AguiChatElement
    el.setAttribute('mode', 'inline')
    el.setAttribute('persist-thread', 'off')
    document.body.appendChild(el)
    await new Promise((r) => setTimeout(r, 0))
    const ms = await fastest(() => {
      const log = el.shadowRoot!.querySelector('.log')!
      log.replaceChildren()
      for (let i = 0; i < 200; i++) {
        const d = document.createElement('div')
        d.className = i % 2 ? 'msg ai' : 'msg me'
        d.innerHTML = md(`Message **${i}** with a [link](https://example.com) and a list:\n- one\n- two`)
        log.appendChild(d)
      }
    }, 3)
    within('200 messages', ms, 120)
    vi.unstubAllGlobals()
  })
})

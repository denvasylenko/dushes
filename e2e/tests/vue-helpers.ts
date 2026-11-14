/**
 * Helpers for the Vue benchmark's stands (e2e/vue/stands/*), no model: a scripted agent shows a change card, the
 * test accepts it, and the check reads the stand's Vue state (window.__stand.values()), never the DOM's values.
 * Stands are built with the package's adapter by default (`cd e2e/vue && npx vite build`, into dist/official); STAND_DIST=reference
 * runs the same checks on QA's reference adapter (`STAND_ADAPTER=reference npx vite build`, into dist/reference), to tell a wrong stand from
 * a missing adapter.
 */
import { expect, type Page } from '@playwright/test'

import { run, type Event } from './agent'

export { run }

export const DIST = `dist/${process.env.STAND_DIST || 'official'}`   // STAND_DIST=reference: QA's reference adapter
export const stand = (name: string) => `/e2e/vue/${DIST}/stands/${name}/index.html`

export type Change = { name: string; label: string; value: unknown; display: string; previous?: unknown; previous_display?: string | null }
let cardNo = 0   // every card has its own id: the widget answers a card id once
export const card = (changes: Change[]): Event => ({ type: 'CUSTOM', name: 'on_interrupt',
  value: JSON.stringify({ type: 'set_fields', card_id: `c${++cardNo}`, changes: changes.map((c) => ({ previous: null, previous_display: null, reveal: [], ...c })) }) })
export const directive = (target: string): Event => ({ type: 'CUSTOM', name: 'ui_directive', value: { target, hint: 'Here', reveal: [] } })

/** The scripted agent: /agent/layouts registers, /agent/run answers each run with the next events (an accepted card
 * resumes in a run of its own, so a script lists run() after every card). */
export async function agent(page: Page, ...runs: Event[][]): Promise<Record<string, unknown>[]> {
  const bodies: Record<string, unknown>[] = []
  calls = bodies
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jsx_hash: 'h', warnings: [] }) }))
  let i = 0
  await page.route('**/agent/run', async (r) => {
    bodies.push(JSON.parse(r.request().postData() || '{}'))
    const ev = runs[Math.min(i++, runs.length - 1)]
    await r.fulfill({ status: 200, contentType: 'text/event-stream', body: ev.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('') })
  })
  return bodies
}

export async function open(page: Page, name: string): Promise<void> {
  await page.goto(stand(name))
  await page.waitForFunction(() => (window as unknown as { __stand?: { ready: boolean; error: string | null } }).__stand?.ready
    || (window as unknown as { __stand?: { error: string | null } }).__stand?.error, null, { timeout: 10_000 })
  const err = await page.evaluate(() => (window as unknown as { __stand: { error: string | null } }).__stand.error)
  expect(err, 'the Vue adapter is ready').toBeNull()
}

export const values = (page: Page) => page.evaluate(() => (window as unknown as { __stand: { values: () => Record<string, unknown> } }).__stand.values())

export async function ask(page: Page, text: string): Promise<void> {
  const box = page.locator('agui-chat textarea:not(.pop-in)')
  await box.fill(text)
  await box.press('Enter')
}

/** Accept the newest card and wait until it says it is filled in, as a person waits before typing again. */
let calls: Record<string, unknown>[] = []
export async function accept(page: Page): Promise<void> {
  const done = await page.locator('agui-chat .card .ok-line').count(), sent = calls.length
  await page.locator('agui-chat .card .btn.pri:visible').last().click()
  await expect(page.locator('agui-chat .card .ok-line')).toHaveCount(done + 1)
  await expect.poll(() => calls.length).toBeGreaterThan(sent)   // the run that resumes after the card was sent
  await expect(page.locator('agui-chat .wait')).toHaveCount(0)   // ... and has ended
}

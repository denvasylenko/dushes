/** The Nuxt 3 stand of the Vue benchmark: the form is server-rendered, the adapter works after hydration. */
import { expect, test } from '@playwright/test'

import { accept, agent, ask, card, run, values } from './vue-helpers'

const NUXT = 'http://127.0.0.1:4400/'

test('the server renders the form; nothing in the adapter touches the browser during SSR', async ({ request }) => {
  const r = await request.get(NUXT)
  expect(r.status()).toBe(200)
  const html = await r.text()
  expect(html).toContain('id="ssr-form"')
  expect(html).toContain('data-name="email"')
})

test('after hydration a card writes the Vue state', async ({ page }) => {
  await agent(page, run(card([{ name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee' },
                              { name: 'guests', label: 'Guests', value: 4, display: '4' }])), run())
  await page.goto(NUXT)
  await page.waitForFunction(() => { const s = (window as unknown as { __stand?: { ready: boolean; error: string | null } }).__stand; return !!s && (s.ready || !!s.error) }, null, { timeout: 15_000 })
  expect(await page.evaluate(() => (window as unknown as { __stand: { error: string | null } }).__stand.error), 'the Vue adapter is ready').toBeNull()
  await ask(page, 'Ann Lee, 4 guests')
  await accept(page)
  await expect.poll(() => values(page)).toMatchObject({ name: 'Ann Lee', guests: 4 })
})

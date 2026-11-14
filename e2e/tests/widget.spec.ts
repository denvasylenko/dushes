/**
 * The <agui-chat> widget in real browser engines (Chromium, Firefox, WebKit) at a phone and a laptop width: what the
 * owner asked to work everywhere. The agent is scripted (agent.ts); Playwright's CSS locators reach into the widget's
 * open shadow root.
 */
import { expect, test, type Page } from '@playwright/test'

import { agent, fakeMic, run, suggestions, text } from './agent'

const composer = (page: Page) => page.locator('agui-chat textarea:not(.pop-in)')

async function open(page: Page, attrs: Record<string, string> = {}): Promise<void> {
  await page.goto('/e2e/fixtures/chat.html')
  await page.waitForFunction(() => !!customElements.get('agui-chat'))
  if (Object.keys(attrs).length) {
    await page.evaluate((a) => { const el = document.querySelector('agui-chat')!; for (const [k, v] of Object.entries(a)) el.setAttribute(k, v) }, attrs)
  }
  await expect(composer(page)).toBeVisible()
}

async function say(page: Page, message: string): Promise<void> {
  await composer(page).fill(message)
  await composer(page).press('Enter')
}

const box = async (page: Page, sel: string) => (await page.locator(sel).first().boundingBox())!

test('the status line does not move the composer', async ({ page }) => {
  await agent(page, { delayMs: 5500, events: run(...text('m1', 'Here is your answer.')) })
  await open(page)
  const before = await box(page, 'agui-chat textarea:not(.pop-in)')
  await say(page, 'hello')
  const wait = page.locator('agui-chat .wait')
  await expect(wait).toBeVisible()
  const dots = await box(page, 'agui-chat .wait')
  const during = await box(page, 'agui-chat textarea:not(.pop-in)')
  await expect(page.locator('agui-chat .wait .slow')).toBeVisible({ timeout: 6000 })   // "Still working…" after a few seconds
  const slow = await box(page, 'agui-chat .wait')
  const later = await box(page, 'agui-chat textarea:not(.pop-in)')
  expect(Math.abs(during.y - before.y)).toBeLessThanOrEqual(1)
  expect(Math.abs(later.y - before.y)).toBeLessThanOrEqual(1)
  expect(Math.abs(slow.height - dots.height)).toBeLessThanOrEqual(1)   // the status keeps its height when its text changes
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Here is your answer.')
})

test('a message sent while it answers waits in the queue, then goes by itself', async ({ page }) => {
  const bodies = await agent(page, { delayMs: 2000, events: run(...text('m1', 'First answer.')) },
                             { events: run(...text('m2', 'Second answer.')) })
  await open(page)
  await say(page, 'first question')
  await expect(page.locator('agui-chat .wait')).toBeVisible()
  await say(page, 'second question')
  await expect(page.locator('agui-chat .msg.queued')).toHaveCount(1)
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Second answer.', { timeout: 8000 })
  await expect(page.locator('agui-chat .msg.queued')).toHaveCount(0)
  expect(bodies).toHaveLength(2)
})

test('suggestions show above the field and a tap sends one', async ({ page }) => {
  const bodies = await agent(page, { events: run(...text('m1', 'Done.'), suggestions('What next?', 'Thanks')) },
                             { events: run(...text('m2', 'Next is the date.')) })
  await open(page)
  await say(page, 'hi')
  const chips = page.locator('agui-chat .quick .chip')
  await expect(chips).toHaveText(['What next?', 'Thanks'])
  await expect.poll(async () => {   // once the row has settled: above the composer, not over it
    const chip = (await chips.first().boundingBox())!, field = await box(page, 'agui-chat .box')
    return chip.y + chip.height <= field.y + 1
  }).toBe(true)
  await chips.first().click()
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Next is the date.')
  expect(JSON.stringify(bodies[1])).toContain('What next?')
})

test('selecting text in an answer opens the reply window; the reply carries the quote', async ({ page }) => {
  const bodies = await agent(page, { events: run(...text('m1', 'The fee is 2% of the amount. It is paid once.')) },
                             { events: run(...text('m2', 'Yes, once.')) })
  await open(page)
  await say(page, 'fees?')
  const answer = page.locator('agui-chat .msg.ai .body p').last()
  await expect(answer).toHaveText(/The fee is 2%/)
  const b = (await answer.boundingBox())!
  await page.mouse.move(b.x + 1, b.y + b.height / 2)   // a real drag over the first words, as a person selects
  await page.mouse.down()
  await page.mouse.move(b.x + b.width * 0.3, b.y + b.height / 2, { steps: 10 })
  await page.mouse.up()
  await page.locator('agui-chat .cap-reply').click()   // step two: the capsule's Reply opens the window
  const pop = page.locator('agui-chat .sel-pop')
  await expect(pop).toBeVisible()
  await expect(page.locator('agui-chat .pop-q')).toHaveText(/The fee/)
  await page.locator('agui-chat .pop-in').fill('is that per month?')
  await page.locator('agui-chat .pop-in').press('Enter')
  await expect(page.locator('agui-chat .reply-chip')).toHaveCount(1)
  await composer(page).press('Enter')   // the quote with its reply goes without other text
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Yes, once.')
  const reply = (bodies[1].forwardedProps as { reply_to?: { quote: string; note?: string }[] }).reply_to
  expect(reply?.[0].quote).toMatch(/^The fee/)
})

test('Esc closes the reply window', async ({ page }) => {
  await agent(page, { events: run(...text('m1', 'The fee is 2% of the amount.')) })
  await open(page)
  await say(page, 'fees?')
  const answer = page.locator('agui-chat .msg.ai .body p').last()
  await expect(answer).toHaveText(/fee/)
  await answer.dblclick({ position: { x: 20, y: 8 } })   // a double click on the first word selects it in every engine
  await page.locator('agui-chat .cap-reply').click()
  await expect(page.locator('agui-chat .sel-pop')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.locator('agui-chat .sel-pop')).toBeHidden()
})

test('Esc stops an answer and brings the suggestions back', async ({ page }) => {
  await agent(page, { events: run(...text('m1', 'Ok.'), suggestions('Book a time')) },
              { delayMs: 8000, events: run(...text('m2', 'Too late.')) })
  await open(page)
  await say(page, 'hi')
  await expect(page.locator('agui-chat .quick .chip')).toHaveText(['Book a time'])
  await say(page, 'a slow one')
  await expect(page.locator('agui-chat .wait')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.locator('agui-chat .wait')).toBeHidden()
  await expect(page.locator('agui-chat .quick .chip')).toHaveText(['Book a time'])
})

test('the mic records and the server writes the text (the fallback for browsers without speech)', async ({ page, browserName }) => {
  test.fixme(browserName === 'webkit', 'headless WebKit with a Web Audio microphone starts or stops the recording only sometimes; check on a real Safari')
  await fakeMic(page)
  await agent(page, { events: run() })
  const sent: { language: string | null; size: number }[] = []
  await page.route('**/agent/transcribe', async (route) => {
    const raw = route.request().postDataBuffer() || Buffer.alloc(0)
    const lang = /name="language"\r\n\r\n([^\r\n]*)/.exec(raw.toString('latin1'))
    sent.push({ language: lang ? lang[1] : null, size: raw.length })
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ text: 'book a table for two', language: 'en' }) })
  })
  await open(page, { voice: 'server' })
  const mic = page.locator('agui-chat .mic')
  await expect(mic).toBeVisible()
  await mic.click()
  await page.waitForTimeout(1200)   // a second of "speech"
  await mic.click()
  await expect(composer(page)).toHaveValue(/book a table for two/, { timeout: 8000 })
  expect(sent).toHaveLength(1)
  expect(sent[0].language).toBe('en')   // the chat's language goes with the audio
  expect(sent[0].size).toBeGreaterThan(500)   // some audio was recorded
})

test('a picture opens large; the browser keeps its own menu (Copy, Save); Esc closes it', async ({ page }) => {
  await agent(page, { events: run() })
  await open(page)
  await page.evaluate(() => {   // the host's upload (a real page posts the file to its server)
    (document.querySelector('agui-chat') as unknown as { options: object }).options =
      { upload: async (f: File) => ({ id: 'a1', filename: f.name }) }
  })
  await expect(page.locator('agui-chat .clip')).toBeVisible()
  // a 64x64 PNG picked as an attachment, as a person adds a photo
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAeklEQVR4nO3PUQkAIBTAwJfEnEY0liH8OITBAtxm7fN1wwUNaEEDWtCAFjSgBQ1oQQNa0IAWNKAFDWhBA1rQgBY0oAUNaEEDWtCAFjSgBQ1oQQNa0IAWNKAFDWhBA1rQgBY0oAUNaEEDWtCAFjSgBQ1oQQNa0IAWPHYBfXDhPC2QOT8AAAAASUVORK5CYII=', 'base64')
  await page.locator('agui-chat input[type=file]').first().setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: png })
  await page.locator('agui-chat .att-open').first().click()
  const zoom = page.locator('agui-chat dialog.zoom')
  await expect(zoom).toBeVisible({ timeout: 10_000 })   // the viewer's tools load on first use
  const img = zoom.locator('img').first()
  await expect(img).toBeVisible()
  expect(await img.evaluate((i) => (i as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)   // a real, loaded image
  const prevented = await img.evaluate((i) => {
    const e = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, composed: true })
    i.dispatchEvent(e)
    return e.defaultPrevented
  })
  expect(prevented).toBe(false)   // nothing swallows the right click: the browser's Copy / Save image menu shows
  await page.keyboard.press('Escape')
  await expect(zoom).toBeHidden()
})

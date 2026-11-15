/**
 * The <agui-chat> widget in real browser engines (Chromium, Firefox, WebKit) at a phone and a laptop width: what the
 * owner asked to work everywhere. The agent is scripted (agent.ts); Playwright's CSS locators reach into the widget's
 * open shadow root.
 */
import { expect, test, type Page } from '@playwright/test'

import { agent, fakeMic, run, slowAgent, suggestions, text } from './agent'

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
  // wait for the upload to end: then the tile has its remove button, and a tap in the MIDDLE of the picture must still
  // open it, not remove it (the remove target once covered the tile's centre: found as a "flake" on a busy machine)
  await expect(page.locator('agui-chat .files .att:not(.busy)')).toBeVisible()
  const tile = page.locator('agui-chat .att-open').first()
  const box = (await tile.boundingBox())!
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
  await expect(page.locator('agui-chat .files .att')).toHaveCount(1)   // still attached
  const zoom = page.locator('agui-chat dialog.zoom')
  await expect(zoom).toBeVisible({ timeout: 10_000 })   // the viewer's tools load on first use
  const img = zoom.locator('img').first()
  await expect(img).toBeVisible()
  await expect.poll(() => img.evaluate((i) => (i as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)   // a real, loaded image (visible can come before it decodes)
  const prevented = await img.evaluate((i) => {
    const e = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, composed: true })
    i.dispatchEvent(e)
    return e.defaultPrevented
  })
  expect(prevented).toBe(false)   // nothing swallows the right click: the browser's Copy / Save image menu shows
  await page.keyboard.press('Escape')
  await expect(zoom).toBeHidden()
})

test('a year on a field card shows without a thousands separator (2019, not 2,019)', async ({ page }) => {
  const card = { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'set_fields', card_id: 'y1', changes: [
    { name: 'year', label: 'Baujahr', kind: 'number', value: 2019, display: '2019', previous: null, previous_display: null, reveal: [] }] }) }   // the payload live v9 sends (SRE)
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"jsx_hash":"h"}' }))
  await agent(page, { events: run(card) })
  await open(page)
  await page.evaluate(() => {   // the formguide plugin, as a page with a form uses it
    const el = document.querySelector('agui-chat') as unknown as { use: (p: unknown) => void }
    const fg = (window as unknown as { AguiChat: { formguide: (o: unknown) => unknown } }).AguiChat.formguide
    el.use(fg({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({ props: {}, state: {} }) }))
  })
  await say(page, 'Es ist von 2019')
  const shown = page.locator('agui-chat .card').first()
  await expect(shown).toBeVisible()
  await expect(shown).not.toContainText('2,019')
  await expect(shown).not.toContainText('2.019')
  await expect(shown).toContainText('2019')
})

test('a field the server marks as a year shows its number as written, whatever its name (built: 2019)', async ({ page }) => {
  const card = { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'set_fields', card_id: 'y2', changes: [
    { name: 'built', label: 'Baujahr', kind: 'year', value: 2019, display: '2019', previous: null, previous_display: null, reveal: [] }] }) }   // the server says what the field is (Owner); the widget groups only kind number
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"jsx_hash":"h"}' }))
  await agent(page, { events: run(card) })
  await open(page)
  await page.evaluate(() => {   // the formguide plugin, as a page with a form uses it
    const el = document.querySelector('agui-chat') as unknown as { use: (p: unknown) => void }
    const fg = (window as unknown as { AguiChat: { formguide: (o: unknown) => unknown } }).AguiChat.formguide
    el.use(fg({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({ props: {}, state: {} }) }))
  })
  await say(page, 'Es ist von 2019')
  const shown = page.locator('agui-chat .card').first()
  await expect(shown).toBeVisible()
  await expect(shown).not.toContainText('2,019')
  await expect(shown).not.toContainText('2.019')
  await expect(shown).toContainText('2019')
})

test('a four-digit number is not grouped even when the server does not mark it (built: 2019, kind number)', async ({ page }) => {
  const card = { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'set_fields', card_id: 'y3', changes: [
    { name: 'built', label: 'Baujahr', kind: 'number', value: 2019, display: '2019', previous: null, previous_display: null, reveal: [] }] }) }   // an unmarked year: the widget groups from five digits on
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"jsx_hash":"h"}' }))
  await agent(page, { events: run(card) })
  await open(page)
  await page.evaluate(() => {   // the formguide plugin, as a page with a form uses it
    const el = document.querySelector('agui-chat') as unknown as { use: (p: unknown) => void }
    const fg = (window as unknown as { AguiChat: { formguide: (o: unknown) => unknown } }).AguiChat.formguide
    el.use(fg({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({ props: {}, state: {} }) }))
  })
  await say(page, 'Es ist von 2019')
  const shown = page.locator('agui-chat .card').first()
  await expect(shown).toBeVisible()
  await expect(shown).not.toContainText('2,019')
  await expect(shown).not.toContainText('2.019')
  await expect(shown).toContainText('2019')
})

test('a German conversation on an English page: the card speaks German, the page stays English, a new chat is English again', async ({ page }) => {
  const ask = { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'ask', card_id: 'q1', language: 'de',
    question: 'Wie wird das Auto genutzt?', options: [{ id: 'personal', label: 'Privat' }, { id: 'business', label: 'Geschäftlich' }] }) }
  const lang = { type: 'CUSTOM', name: 'language', value: { lang: 'de' } }   // the server names the conversation's language (18db8fe)
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"jsx_hash":"h"}' }))
  await agent(page, { events: run(lang, ...text('m1', 'Gern.'), ask) }, { events: run(...text('m2', 'Sure.')) })
  await open(page)
  await page.evaluate(() => {
    const el = document.querySelector('agui-chat') as unknown as { use: (p: unknown) => void }
    const fg = (window as unknown as { AguiChat: { formguide: (o: unknown) => unknown } }).AguiChat.formguide
    el.use(fg({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({ props: {}, state: {} }) }))
  })
  const placeholder = await composer(page).getAttribute('placeholder')
  await say(page, 'Ich möchte ein Angebot für mein Auto.')
  const card = page.locator('agui-chat .card').first()
  await expect(card).toContainText('Privat')
  await expect(card).toContainText('Überspringen')                       // the card's own words follow the conversation
  await expect(card).not.toContainText('Skip')
  expect(await composer(page).getAttribute('placeholder')).toBe(placeholder)   // the page's own words stay English
  await page.evaluate(() => (document.querySelector('agui-chat') as unknown as { reset: () => void }).reset())   // a new chat
  await say(page, 'Hello')
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Sure.')
  await expect(page.locator('agui-chat')).not.toContainText('Überspringen')
})

test('the composer text sits level with its buttons (empty, one line, three lines; touch and desktop, light and dark, hero)', async ({ browser }, info) => {
  test.skip(info.project.name.endsWith('-phone'), 'this test makes its own phone and desktop contexts: once per engine')
  const firefox = info.project.name.startsWith('firefox')   // Firefox has no touch emulation flag
  const failures: string[] = []
  for (const size of [{ name: 'touch 390', viewport: { width: 390, height: 844 }, hasTouch: true }, { name: 'desktop 1280', viewport: { width: 1280, height: 800 }, hasTouch: false }]) {
    if (size.hasTouch && firefox) continue
    for (const scheme of ['light', 'dark'] as const) {
      for (const mode of ['inline', 'hero']) {
        const ctx = await browser.newContext({ viewport: size.viewport, hasTouch: size.hasTouch, colorScheme: scheme })
        const page = await ctx.newPage()
        await page.route('**/agent/**', (r) => r.fulfill({ status: 404, body: '' }))
        await page.goto('http://127.0.0.1:4399/e2e/fixtures/chat.html')
        await page.waitForFunction(() => !!customElements.get('agui-chat'))
        await page.evaluate((m) => { const el = document.querySelector('agui-chat')!; el.setAttribute('mode', m); el.setAttribute('mic', 'on'); el.setAttribute('voice', 'server') }, mode)
        const field = page.locator('agui-chat textarea:not(.pop-in)')
        await expect(field).toBeVisible()
        for (const [state, value] of [['empty', ''], ['one line', 'Hello there'], ['three lines', 'one\ntwo\nthree']] as const) {
          await field.fill(value)
          await page.waitForTimeout(80)   // the field grows on input
          const m = await page.evaluate(() => {
            const r = document.querySelector('agui-chat')!.shadowRoot!
            const t = r.querySelector('textarea:not(.pop-in)') as HTMLTextAreaElement, cs = getComputedStyle(t), b = t.getBoundingClientRect()
            const lh = parseFloat(cs.lineHeight), centre = (sel: string) => { const e = r.querySelector(sel) as HTMLElement | null; if (!e || e.hidden || !e.offsetParent) return null; const x = e.getBoundingClientRect(); return x.top + x.height / 2 }
            return { first: b.top + parseFloat(cs.paddingTop) + lh / 2, last: b.bottom - parseFloat(cs.paddingBottom) - lh / 2, send: centre('.send'), mic: centre('.mic') }
          })
          const text = state === 'three lines' ? m.last : m.first   // a tall field: its last line stays level with the buttons
          for (const [name, c] of [['send', m.send], ['mic', m.mic]] as const) {
            if (c !== null && Math.abs(text - c) > 1) failures.push(`${size.name} ${scheme} ${mode} ${state}: text ${text.toFixed(1)} vs ${name} ${c.toFixed(1)}`)
          }
        }
        await ctx.close()
      }
    }
  }
  expect(failures, failures.join('\n')).toEqual([])
})

test('replying to a quote of your own message carries that message id and the quote', async ({ page }) => {
  const bodies = await agent(page, { events: run(...text('m1', 'Noted.')) }, { events: run(...text('m2', 'Yes, on Friday.')) })
  await open(page)
  await say(page, 'Please book a table for Friday evening')
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Noted.')
  const mine = page.locator('agui-chat .msg.me .bubble').last()
  await mine.dblclick({ position: { x: 24, y: 10 } })   // select a word of my own bubble
  await page.locator('agui-chat .cap-reply').click()
  const field = page.locator('agui-chat .pop-in')
  await expect(field).toBeVisible()
  await expect(field).toHaveAttribute('placeholder', 'Reply to your message')
  await field.fill('I meant this Friday')
  await field.press('Enter')
  await expect(page.locator('agui-chat .reply-chip')).toHaveCount(1)
  await composer(page).press('Enter')
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Yes, on Friday.')
  const sent = bodies[1] as { forwardedProps: { reply_to?: { message_id: string; quote: string }[] }; messages: { id: string; role: string; content: string }[] }
  const reply = sent.forwardedProps.reply_to
  expect(reply).toHaveLength(1)
  expect('Please book a table for Friday evening').toContain(reply![0].quote)
  const own = sent.messages.find((m) => m.role === 'user' && m.content.includes('book a table'))
  expect(reply![0].message_id).toBe(own?.id)   // my message's own id
})

test('the steps line ("Done in N s") never sits above the first message (complaint 16)', async ({ page }) => {
  const steps = [{ type: 'TOOL_CALL_START', toolCallId: 't1', toolCallName: 'search_site' }, { type: 'TOOL_CALL_ARGS', toolCallId: 't1', delta: '{"query":"hours"}' },
                 { type: 'TOOL_CALL_END', toolCallId: 't1' }, { type: 'TOOL_CALL_RESULT', messageId: 't1-result', toolCallId: 't1', content: 'found', role: 'tool' }]
  await slowAgent(page, [run(...steps, ...text('m1', 'We are open until 19:00.'))])   // ~3.5 s: the steps line shows
  await open(page, { 'tool-steps': 'on' })
  await say(page, 'When are you open?')
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('We are open until 19:00.', { timeout: 15_000 })
  const order = await page.evaluate(() => {
    const log = document.querySelector('agui-chat')!.shadowRoot!.querySelector('.log')!
    const kids = [...log.children] as HTMLElement[]
    const top = (sel: string) => { const e = kids.find((k) => k.matches(sel) && !k.hidden); return e ? e.getBoundingClientRect().top : null }
    return { me: top('.msg.me'), steps: top('.steps'), dom: kids.filter((k) => !k.hidden).map((k) => k.className).slice(0, 6) }
  })
  expect(order.me, 'the user message is in the log').not.toBeNull()
  expect(order.steps, 'a turn this long shows its steps line').not.toBeNull()
  expect(order.steps!, `log order: ${order.dom.join(' | ')}`).toBeGreaterThan(order.me!)
})

test('a host-started run: the steps line of a turn the user did not start does not sit above their first message (complaint 16, path 1)', async ({ page }) => {
  const steps = [{ type: 'TOOL_CALL_START', toolCallId: 't1', toolCallName: 'get_fields' }, { type: 'TOOL_CALL_ARGS', toolCallId: 't1', delta: '{}' },
                 { type: 'TOOL_CALL_END', toolCallId: 't1' }, { type: 'TOOL_CALL_RESULT', messageId: 't1-result', toolCallId: 't1', content: 'ok', role: 'tool' }]
  await slowAgent(page, [run(...steps, ...text('m1', 'Welcome back. I prefilled what I know.')), run(...text('m2', 'Sure.'))])
  await open(page, { 'tool-steps': 'on' })
  await page.evaluate(() => (document.querySelector('agui-chat') as unknown as { run: (o: unknown) => Promise<void> }).run({ forwardedProps: { prefill: { data: { name: 'Ann' } } } }))
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Welcome back. I prefilled what I know.', { timeout: 15_000 })
  await say(page, 'Thanks, what next?')
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('Sure.', { timeout: 15_000 })
  const seen = await page.evaluate(() => {
    const kids = [...document.querySelector('agui-chat')!.shadowRoot!.querySelector('.log')!.children] as HTMLElement[]
    const shown = kids.filter((k) => !k.hidden && k.getBoundingClientRect().height > 0)
    const first = shown.find((k) => k.matches('.msg.me'))!
    return { above: shown.filter((k) => k.matches('.steps') && k.getBoundingClientRect().top < first.getBoundingClientRect().top).map((k) => k.textContent), order: shown.map((k) => k.className).slice(0, 6) }
  })
  if (process.env.QA_DEBUG) console.log('ORDER', JSON.stringify(seen))
  expect(seen.above, `a steps line above the first user message; log: ${seen.order.join(' | ')}`).toEqual([])
})

/** A thread for card_focus: a field card f1, a long answer that pushes it out of sight, then runs that point at f1
 *  and at a card that is gone. Returns the request bodies and "is f1 inside the log's visible area". */
async function focusThread(page: Page) {
  const card = { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'set_fields', card_id: 'f1', changes: [
    { name: 'city', label: 'City', kind: 'text', value: 'Bologna', display: 'Bologna', previous: null, previous_display: null, reveal: [] }] }) }
  const long = Array.from({ length: 40 }, (_x, i) => `Line ${i + 1} of a long answer.`).join('\n\n')
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"jsx_hash":"h"}' }))
  const bodies = await agent(page, { events: run(card) }, { events: run(...text('a2', long)) },
    { events: run(...text('a3', 'Here is that card.'), { type: 'CUSTOM', name: 'card_focus', value: { card_id: 'f1' } }) },
    { events: run(...text('a4', 'Here is that card.'), { type: 'CUSTOM', name: 'card_focus', value: { card_id: 'gone' } }) })
  await open(page)
  await page.evaluate(() => {
    const el = document.querySelector('agui-chat') as unknown as { use: (p: unknown) => void; addEventListener: (n: string, f: (e: Event) => void) => void }
    const fg = (window as unknown as { AguiChat: { formguide: (o: unknown) => unknown } }).AguiChat.formguide
    el.use(fg({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({ props: {}, state: {} }) }))
    el.addEventListener('agui:card-missing', (e) => { (window as unknown as { missing: unknown }).missing = (e as CustomEvent).detail })
  })
  const inLog = () => page.evaluate(() => {
    const r = document.querySelector('agui-chat')!.shadowRoot!
    const c = r.querySelector('[data-card-id="f1"]')!.getBoundingClientRect(), log = r.querySelector('.log')!.getBoundingClientRect()
    return c.top >= log.top - 1 && c.bottom <= log.bottom + 1
  })
  await say(page, 'I live in Bologna')
  await expect(page.locator('agui-chat [data-card-id="f1"]')).toBeVisible()
  await say(page, 'Tell me more')
  await expect(page.locator('agui-chat')).toContainText('Line 40 of a long answer.')
  await expect.poll(inLog).toBe(false)   // the long answer pushed the card out of sight (the log follows it a moment later)
  return { bodies, inLog }
}

test('card_focus: a card still in the thread is scrolled to and highlighted, never drawn twice; a missing one says so', async ({ page }) => {
  const { bodies, inLog } = await focusThread(page)
  const shown = page.locator('agui-chat [data-card-id="f1"]')
  await say(page, 'Show me that card again')
  await expect(page.locator('agui-chat [data-card-id="f1"][data-spot]')).toHaveCount(1)   // highlighted
  await expect(shown).toHaveCount(1)                                                       // no second card
  await expect.poll(inLog, { timeout: 4000 }).toBe(true)                                   // scrolled into the log's visible area
  // the focus stays in the composer: the person just sent a message and keeps typing (Design, 2026-11-14)
  expect(await page.evaluate(() => document.querySelector('agui-chat')!.shadowRoot!.activeElement?.tagName)).toBe('TEXTAREA')
  await expect(page.locator('agui-chat [data-card-id="f1"][data-spot]')).toHaveCount(0, { timeout: 4000 })   // the glow ends
  expect((bodies[bodies.length - 1].forwardedProps as { capabilities?: string[] }).capabilities).toContain('card.focus')
  await say(page, 'And the other one')
  await expect.poll(() => page.evaluate(() => (window as unknown as { missing?: { card_id: string } }).missing?.card_id)).toBe('gone')
  await expect(page.locator('agui-chat [data-card-id]')).toHaveCount(1)
})

test('card_focus with reduced motion: the log jumps to the card at once, no glide', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const { inLog } = await focusThread(page)
  await say(page, 'Show me that card again')
  await expect(page.locator('agui-chat [data-card-id="f1"][data-spot]')).toHaveCount(1)
  await page.waitForTimeout(100)
  expect(await inLog()).toBe(true)   // there within 100 ms of the highlight
})

test('on a touch screen a tap in the middle of an attached picture opens it, never removes it', async ({ browser }, info) => {
  // Found as a "flake" on 2026-11-15: with a coarse pointer the remove button's enlarged tap target covered the tile's
  // centre, so once the upload had finished a tap on one's own photo removed it. A mouse does not show it.
  test.skip(!info.project.name.endsWith('-phone') || info.project.name.startsWith('firefox'), 'touch emulation: Chromium and WebKit, once each')
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })
  const page = await ctx.newPage()
  await agent(page, { events: run() })
  await page.goto('http://127.0.0.1:4399/e2e/fixtures/chat.html')
  await page.waitForFunction(() => !!customElements.get('agui-chat'))
  await page.evaluate(() => {
    (document.querySelector('agui-chat') as unknown as { options: object }).options = { upload: async (f: File) => ({ id: 'a1', filename: f.name }) }
  })
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64')
  await page.locator('agui-chat input[type=file]').first().setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: png })
  const tile = page.locator('agui-chat .files .att')
  await expect(page.locator('agui-chat .files .att:not(.busy)')).toBeVisible()   // uploaded: the remove button is there now
  expect(await page.evaluate(() => matchMedia('(pointer: coarse)').matches)).toBe(true)
  const box = (await tile.first().boundingBox())!
  await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2)
  await expect(page.locator('agui-chat dialog.zoom')).toBeVisible({ timeout: 10_000 })   // the picture opened
  await expect(tile).toHaveCount(1)                                                       // and is still attached
  await ctx.close()
})

// ---------------------------------------------------------------------------------------------- the + menu
// The owner (2026-11-15): the plus is a menu, not an attach button, even while it holds one or two rows.

async function openWithUpload(page: Page, options = '{}'): Promise<void> {
  await agent(page, { events: run() })
  await open(page)
  await page.evaluate((extra) => {
    (document.querySelector('agui-chat') as unknown as { options: object }).options =
      { upload: async (f: File) => ({ id: 'a1', filename: f.name }), ...JSON.parse(extra) }
  }, options)
  await expect(page.locator('agui-chat .clip')).toBeVisible()
}

test('the plus opens a menu; the file picker opens only from its row', async ({ page }) => {
  await openWithUpload(page)
  const plus = page.locator('agui-chat .clip'), menu = page.locator('agui-chat .menu[role=menu]')
  let pickers = 0
  page.on('filechooser', () => { pickers += 1 })
  await plus.click()
  await expect(menu).toBeVisible()
  await expect(plus).toHaveAttribute('aria-expanded', 'true')
  await page.waitForTimeout(300)
  expect(pickers).toBe(0)                                     // the plus alone never opens the picker
  const files = menu.locator('button[role=menuitem][data-id=files]')
  await expect(files.locator('.menu-l')).toHaveText(/files|photos/i)
  const chooser = page.waitForEvent('filechooser')
  await files.click()
  await chooser
  await expect(menu).toHaveCount(0)                           // a pick closes the menu
})

test('the plus says it opens a menu before it is ever opened (aria-haspopup, aria-expanded)', async ({ page }) => {
  await openWithUpload(page)
  const plus = page.locator('agui-chat .clip')
  await expect(plus).toHaveAttribute('aria-haspopup', 'menu')   // a screen reader hears "menu" on the button itself
  await expect(plus).toHaveAttribute('aria-expanded', 'false')
})

test('the plus menu closes on Escape, on a press outside and on the plus itself, and never covers the field', async ({ page }) => {
  await openWithUpload(page)
  const plus = page.locator('agui-chat .clip'), menu = page.locator('agui-chat .menu[role=menu]')
  await plus.click()
  await expect(menu).toBeVisible()
  const m = (await menu.boundingBox())!, f = (await composer(page).boundingBox())!, view = page.viewportSize()!
  expect(m.y + m.height).toBeLessThanOrEqual(f.y + 1)        // above the field, not over it
  expect(m.x).toBeGreaterThanOrEqual(0)
  expect(m.x + m.width).toBeLessThanOrEqual(view.width)       // inside the screen at 390 px too
  await page.keyboard.press('Escape')
  await expect(menu).toHaveCount(0)
  await expect(plus).toBeFocused()                            // focus goes back where it came from
  await expect(plus).toHaveAttribute('aria-expanded', 'false')
  await plus.click()
  await expect(menu).toBeVisible()
  await page.mouse.click(view.width / 2, 20)                  // a press outside
  await expect(menu).toHaveCount(0)
  await plus.click()
  await expect(menu).toBeVisible()
  await plus.click()                                          // the plus is a toggle
  await expect(menu).toHaveCount(0)
})

test('the plus menu works from the keyboard: arrows move, Enter chooses', async ({ page }, info) => {
  test.skip(info.project.name.endsWith('-phone'), 'a hardware keyboard: the laptop size')
  await openWithUpload(page, JSON.stringify({ commands: [{ id: 'help', label: 'Help', send: 'What can you do?' }] }))
  const plus = page.locator('agui-chat .clip'), menu = page.locator('agui-chat .menu[role=menu]')
  await plus.focus()
  await page.keyboard.press('Enter')
  await expect(menu).toBeVisible()
  const rows = menu.locator('button[role=menuitem]')
  expect(await rows.count()).toBeGreaterThanOrEqual(2)        // files and commands
  const focused = () => page.evaluate(() => (document.querySelector('agui-chat')!.shadowRoot!.activeElement as HTMLElement | null)?.dataset.id ?? null)
  await expect.poll(focused).toBe('files')                    // opened from the keyboard: the first row has the focus
  await page.keyboard.press('ArrowDown')
  expect(await focused()).not.toBe('files')                   // the arrow moved it
  await page.keyboard.press('End')
  const last = await focused()
  await page.keyboard.press('Home')
  expect(await focused()).toBe('files')
  expect(last).not.toBe('files')
  const chooser = page.waitForEvent('filechooser')
  await page.keyboard.press('Enter')
  await chooser
})

test('with attachments off and nothing else to offer there is no plus at all', async ({ page }) => {
  await agent(page, { events: run() })
  await open(page)                                            // no upload, no commands, no host rows
  await expect(page.locator('agui-chat .clip')).toBeHidden()
})

// ---------------------------------------------------------------------------------------------- a value the form refuses
// The owner (2026-11-15): a VIN of "555" showed a green check while the text said it was not entered.

const vinAsk = (id: string) => ({ type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'ask', card_id: id,
  question: 'What is the VIN?', field: 'vin', applies: true, label: 'VIN', input: { type: 'text' } }) })

async function useVinForm(page: Page): Promise<void> {
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"jsx_hash":"h"}' }))
  await open(page)
  await page.evaluate(() => {
    const el = document.querySelector('agui-chat') as unknown as { use: (p: unknown) => void }
    const fg = (window as unknown as { AguiChat: { formguide: (o: unknown) => unknown } }).AguiChat.formguide
    let state: Record<string, unknown> = { vin: '' }
    const config = () => ({ props: String(state.vin ?? '').length && String(state.vin).length !== 17 ? { vin: { error: '17 characters' } } : {}, state })
    el.use(fg({ getState: () => ({ config: config(), jsx_hash: 'h' }), applyChanges: async (v: Record<string, unknown>) => { state = { ...state, ...v }; return config() } }))
  })
}

test('a typed value the form refuses: the card shows a cross and the reason, never the green line, and says why to the server', async ({ page }) => {
  const bodies = await agent(page, { events: run(...text('m1', 'Let me take the VIN.'), vinAsk('v1')) }, { events: run(...text('m2', 'A VIN has 17 characters.')) })
  await useVinForm(page)
  await say(page, 'my vin is 555')
  const card = page.locator('agui-chat [data-card-id="v1"]')
  const field = card.locator('input, textarea').first()
  await expect(field).toBeVisible()
  await field.fill('555')
  await field.press('Enter')
  const line = card.locator('.ok-line')
  await expect(line).toHaveClass(/\boff\b/)                   // never the answered line
  await expect(line).toContainText('555')
  await expect(line).toContainText('17 characters')           // the form's own reason
  await expect(line.locator('.btn')).toHaveCount(0)           // nothing to undo: nothing was entered
  await expect(card).toHaveClass(/\bdone\b/)
  await expect(page.locator('agui-chat .msg.ai .body').last()).toHaveText('A VIN has 17 characters.', { timeout: 15_000 })   // the next run, slow on a busy machine
  const resume = (bodies.at(-1) as { forwardedProps: { command: { resume: unknown } } }).forwardedProps.command.resume
  expect(resume).toEqual({ answer: { text: '555' }, rejected: { vin: '17 characters' } })   // the reason, and no config: the form kept its old value
})

test('card_result not_accepted turns an answered card into a refused one, once', async ({ page }) => {
  const refused = { type: 'CUSTOM', name: 'card_result', value: { card_id: 'v2', status: 'not_accepted', reason: 'This VIN is not in the register' } }
  await agent(page, { events: run(...text('m1', 'Let me take the VIN.'), vinAsk('v2')) }, { events: run(refused, refused, ...text('m2', 'That VIN was not accepted.')) })
  await useVinForm(page)
  await say(page, 'here is my vin')
  const card = page.locator('agui-chat [data-card-id="v2"]')
  const field = card.locator('input, textarea').first()
  await field.fill('WVWZZZ1JZXW000001')                        // 17 characters: the form takes it, the server refuses it
  await field.press('Enter')
  const line = card.locator('.ok-line')
  await expect(line).toHaveClass(/\boff\b/)
  await expect(line).toContainText('This VIN is not in the register')
  await expect(line.locator('.btn')).toHaveCount(0)           // Undo is gone
  expect((await line.textContent())!.split('This VIN is not in the register').length - 1).toBe(1)   // sent twice, said once
})

// ---------------------------------------------------------------------------------------------- 16 px inputs on touch
// The owner (2026-11-15): Safari on a phone zooms the page when a focused field's text is under 16 px.

test('on a touch screen every field in the chat has text of at least 16 px (the composer, a question card, a several-fields card)', async ({ browser }, info) => {
  test.skip(!info.project.name.endsWith('-phone') || info.project.name.startsWith('firefox'), 'a touch context: the phone size, engines that emulate touch')
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: info.project.name.startsWith('chromium') })
  const page = await ctx.newPage()
  const typed = { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'ask', card_id: 'i1', question: 'What is the VIN?', field: 'vin',
    applies: true, label: 'VIN', input: { type: 'text' } }) }
  const several = { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'ask', card_id: 'i2', question: 'A few details', fields: [
    { name: 'first_name', label: 'First name', input: { type: 'text' } }, { name: 'age', label: 'Age', input: { type: 'number' } },
    { name: 'start', label: 'Start date', input: { type: 'date' } }] }) }
  await page.route('**/agent/layouts', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"jsx_hash":"h"}' }))
  await agent(page, { events: run(...text('m1', 'One thing first.'), typed) }, { events: run(...text('m2', 'And these.'), several) }, { events: run(...text('m3', 'Thanks.')) })
  await page.goto('http://127.0.0.1:4399/e2e/fixtures/chat.html')
  await page.waitForFunction(() => !!customElements.get('agui-chat'))
  await page.evaluate(() => {
    const el = document.querySelector('agui-chat') as unknown as { use: (p: unknown) => void }
    const fg = (window as unknown as { AguiChat: { formguide: (o: unknown) => unknown } }).AguiChat.formguide
    el.use(fg({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({ props: {}, state: {} }) }))
  })
  const small = () => page.evaluate(() => {
    const root = document.querySelector('agui-chat')!.shadowRoot!
    return [...root.querySelectorAll<HTMLElement>('input:not([type=file]):not([type=checkbox]):not([type=radio]):not([hidden]), textarea, select')]
      .filter((e) => e.offsetParent !== null)
      .map((e) => ({ what: `${e.tagName.toLowerCase()}${e.getAttribute('type') ? `[${e.getAttribute('type')}]` : ''}.${e.className}`, px: parseFloat(getComputedStyle(e).fontSize) }))
      .filter((x) => x.px < 16)
  })
  await expect(composer(page)).toBeVisible()
  expect(await small(), 'the composer').toEqual([])
  await say(page, 'my car')
  const first = page.locator('agui-chat [data-card-id="i1"]').locator('input, textarea').first()
  await expect(first).toBeVisible()
  expect(await small(), 'a question card with a typed answer').toEqual([])
  await first.fill('WVWZZZ1JZXW000001')
  await first.press('Enter')
  await expect(page.locator('agui-chat [data-card-id="i2"]').locator('input').first()).toBeVisible()
  expect(await small(), 'a card with several fields').toEqual([])
  await ctx.close()
})

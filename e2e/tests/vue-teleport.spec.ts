/** Vue benchmark stand: fields inside a modal rendered with <Teleport to="body">, unmounted while closed. */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values, type Change } from './vue-helpers'

const modal = (page: Page) => page.locator('body > .modal-backdrop .modal')   // the teleported DOM, outside the app
const DELIVERY: Change[] = [
  { name: 'address', label: 'Address', value: '12 Rua Augusta', display: '12 Rua Augusta', previous: '', previous_display: '' },
  { name: 'city', label: 'City', value: 'Lisbon', display: 'Lisbon', previous: '', previous_display: '' },
]

test.describe('stand: teleport (fields in a modal teleported to body)', () => {
  test('a card writes the modal\'s fields while the modal is closed', async ({ page }) => {
    await agent(page, run(card(DELIVERY)), run())
    await open(page, 'teleport')
    await expect(modal(page)).toHaveCount(0)
    await ask(page, 'deliver to 12 Rua Augusta, Lisbon')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ address: '12 Rua Augusta', city: 'Lisbon', phone: '', name: '' })
    // after writing, the card shows the field it filled (the widget's design): that opens the modal through onReveal
    await expect.poll(async () => (await values(page)).modalOpen).toBe(true)
    await expect(modal(page).locator('[data-name=address] input')).toHaveValue('12 Rua Augusta')
    await expect(modal(page).locator('[data-name=city] input')).toHaveValue('Lisbon')
  })

  test('a card writes the modal\'s fields while the modal is open; the inputs show them', async ({ page }) => {
    await agent(page, run(card(DELIVERY)), run())
    await open(page, 'teleport')
    await page.locator('form.form .open-delivery').click()
    await expect(modal(page)).toHaveCount(1)
    await ask(page, 'deliver to 12 Rua Augusta, Lisbon')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ address: '12 Rua Augusta', city: 'Lisbon' })
    await expect(modal(page).locator('[data-name=address] input')).toHaveValue('12 Rua Augusta')
    await expect(modal(page).locator('[data-name=city] input')).toHaveValue('Lisbon')
    await expect(page.locator('form.form .summary')).toHaveText('12 Rua Augusta, Lisbon')
  })

  test('"take me there" to a modal field opens the modal and marks the field inside it', async ({ page }) => {
    await agent(page, run(directive('phone')))
    await open(page, 'teleport')
    await expect(modal(page)).toHaveCount(0)
    await ask(page, 'where does my phone number go?')
    await expect.poll(async () => (await values(page)).modalOpen).toBe(true)
    await expect(modal(page).locator('[data-name=phone][data-agui-highlight]')).toHaveCount(1)
  })

  test('Undo puts the modal\'s fields back', async ({ page }) => {
    await agent(page, run(card(DELIVERY)), run())
    await open(page, 'teleport')
    const before = await values(page)
    await ask(page, 'deliver to 12 Rua Augusta, Lisbon')
    await accept(page)
    await expect.poll(async () => (await values(page)).city).toBe('Lisbon')
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(async () => ({ ...(await values(page)), modalOpen: false })).toEqual(before)   // the card opened the modal
  })

  test('nothing else changes: a main-form card leaves the modal\'s fields alone', async ({ page }) => {
    await agent(page, run(card([{ name: 'product', label: 'Product', value: 'Desk lamp', display: 'Desk lamp', previous: '', previous_display: '' }])), run())
    await open(page, 'teleport')
    const before = await values(page)
    await ask(page, 'a desk lamp')
    await accept(page)
    await expect.poll(async () => (await values(page)).product).toBe('Desk lamp')
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'product') expect(after[k], k).toEqual(before[k])
  })
})

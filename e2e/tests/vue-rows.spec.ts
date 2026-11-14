/** Vue benchmark stand: dynamic rows (an invoice, items: [{desc, qty, price}], "Add row", a computed total). */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values } from './vue-helpers'

const field = (page: Page, name: string) => page.locator(`form.form [data-name="${name}"]`)   // the form's own, not the card's

test.describe('stand: rows (an array of rows, Add row, a computed total)', () => {
  test('a card addressing rows by dotted names writes those rows; the total follows', async ({ page }) => {
    await agent(page, run(card([
      { name: 'items.0.qty', label: 'Row 1: quantity', value: 3, display: '3', previous: 1, previous_display: '1' },
      { name: 'items.0.price', label: 'Row 1: unit price', value: 20, display: '20', previous: 0, previous_display: '0' },
      { name: 'items.1.desc', label: 'Row 2: description', value: 'Setup fee', display: 'Setup fee', previous: '', previous_display: '' },
    ])), run())
    await open(page, 'rows')
    await ask(page, 'three of row one at 20, and row two is the setup fee')
    await accept(page)
    await expect.poll(() => values(page)).toEqual({ customer: '', total: 60, items: [
      { desc: '', qty: 3, price: 20 }, { desc: 'Setup fee', qty: 1, price: 0 }] })
    await expect(field(page, 'items.0.qty').locator('input')).toHaveValue('3')
    await expect(field(page, 'items.1.desc').locator('input')).toHaveValue('Setup fee')
    await expect(page.locator('form.form .total')).toHaveText('Total: 60 EUR')
  })

  test('a row the person adds can be filled by the next card', async ({ page }) => {
    await agent(page, run(card([
      { name: 'items.2.desc', label: 'Row 3: description', value: 'Hosting', display: 'Hosting', previous: '', previous_display: '' },
      { name: 'items.2.qty', label: 'Row 3: quantity', value: 12, display: '12', previous: 1, previous_display: '1' },
      { name: 'items.2.price', label: 'Row 3: unit price', value: 9.5, display: '9.50', previous: 0, previous_display: '0' },
    ])), run())
    await open(page, 'rows')
    await page.locator('form.form .add').click()
    await expect.poll(async () => ((await values(page)).items as unknown[]).length).toBe(3)
    await ask(page, 'the new row is 12 months of hosting at 9.50')
    await accept(page)
    await expect.poll(async () => ((await values(page)).items as unknown[])[2]).toEqual({ desc: 'Hosting', qty: 12, price: 9.5 })
    expect((await values(page)).total).toBe(114)
    await expect(field(page, 'items.2.desc').locator('input')).toHaveValue('Hosting')
  })

  test('Undo puts the rows back', async ({ page }) => {
    await agent(page, run(card([{ name: 'items.1.qty', label: 'Row 2: quantity', value: 4, display: '4', previous: 1, previous_display: '1' }])), run())
    await open(page, 'rows')
    const before = await values(page)
    await ask(page, 'four of row two')
    await accept(page)
    await expect.poll(async () => ((await values(page)).items as { qty: number }[])[1].qty).toBe(4)
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(() => values(page)).toEqual(before)
  })

  test('"take me there" to a row cell marks it', async ({ page }) => {
    await agent(page, run(directive('items.1.price')))
    await open(page, 'rows')
    await ask(page, 'where is the price of row two?')
    await expect(page.locator('form.form [data-name="items.1.price"][data-agui-highlight]')).toHaveCount(1)
  })

  test('nothing else changes: other rows and fields stay', async ({ page }) => {
    await agent(page, run(card([{ name: 'items.1.desc', label: 'Row 2: description', value: 'Training', display: 'Training', previous: '', previous_display: '' }])), run())
    await open(page, 'rows')
    await field(page, 'items.0.desc').locator('input').fill('Licence')
    const before = await values(page)
    await ask(page, 'row two is training')
    await accept(page)
    await expect.poll(async () => ((await values(page)).items as { desc: string }[])[1].desc).toBe('Training')
    const after = await values(page) as { items: Record<string, unknown>[]; customer: string }
    const was = before as typeof after
    expect(after.customer).toBe(was.customer)
    expect(after.items[0]).toEqual(was.items[0])
    expect(after.items[1]).toEqual({ ...was.items[1], desc: 'Training' })
  })

  // The schema can only list row slots up front (SLOTS = 5 in the stand); a row past them has no field in the layout.
  test.fixme('a row past the declared slots (the sixth) can be filled', async ({ page }) => {   // pending: repeated rows in the layout (Owner, needs CPO agreement)
    await agent(page, run(card([{ name: 'items.5.desc', label: 'Row 6: description', value: 'Travel', display: 'Travel', previous: '', previous_display: '' }])), run())
    await open(page, 'rows')
    for (let i = 0; i < 4; i++) await page.locator('form.form .add').click()
    await ask(page, 'row six is travel')
    await accept(page)
    await expect.poll(async () => ((await values(page)).items as { desc: string }[])[5]?.desc).toBe('Travel')
  })
})

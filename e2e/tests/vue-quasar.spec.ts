/** Vue benchmark stand: Quasar 2 components (q-select, q-select multiple, q-input with q-date, q-slider, q-input). */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values, type Change } from './vue-helpers'

const field = (page: Page, name: string) => page.locator(`form.form [data-name="${name}"]`)   // the form's own, not the card's

const FULL: Change[] = [
  { name: 'company', label: 'Company', value: 'Acme Ltd', display: 'Acme Ltd', previous: '', previous_display: '' },
  { name: 'plan', label: 'Plan', value: { id: 'plus', name: 'Plus' }, display: 'Plus' },
  { name: 'addons', label: 'Add-ons', value: [{ id: 'backup', name: 'Backup' }, { id: 'sso', name: 'Single sign-on' }], display: 'Backup, Single sign-on', previous: [] },
  { name: 'start', label: 'Start date', value: '2026-12-01', display: '1 Dec 2026', previous: '', previous_display: '' },
  { name: 'seats', label: 'Seats', value: 12, display: '12', previous: 5, previous_display: '5' },
]

test.describe('stand: quasar (q-select, q-select multiple, q-date, q-slider, q-input)', () => {
  test('accepting the card writes Vue state in each component\'s own shape', async ({ page }) => {
    await agent(page, run(card(FULL)), run())
    await open(page, 'quasar')
    await ask(page, 'Acme, Plus with backup and SSO from 1 December, 12 seats')
    await accept(page)
    await expect.poll(() => values(page)).toEqual({ company: 'Acme Ltd', plan: 'plus', addons: ['backup', 'sso'], start: '2026-12-01', seats: 12 })
  })

  test('the components show the values', async ({ page }) => {
    await agent(page, run(card(FULL)), run())
    await open(page, 'quasar')
    await ask(page, 'fill it')
    await accept(page)
    await expect(field(page, 'company').locator('input')).toHaveValue('Acme Ltd')
    await expect(field(page, 'plan').locator('.q-field__native')).toHaveText('Plus')
    await expect(field(page, 'addons').locator('.q-field__native')).toContainText('Backup')
    await expect(field(page, 'addons').locator('.q-field__native')).toContainText('Single sign-on')
    await expect(field(page, 'start').locator('input')).toHaveValue('2026-12-01')
    await expect(field(page, 'seats').locator('[role=slider]')).toHaveAttribute('aria-valuenow', '12')
    await expect(field(page, 'seats').locator('.seats')).toHaveText('12')
  })

  test('Undo puts the Vue state back', async ({ page }) => {
    await agent(page, run(card(FULL)), run())
    await open(page, 'quasar')
    const before = await values(page)
    await ask(page, 'fill it')
    await accept(page)
    await expect.poll(async () => (await values(page)).plan).toBe('plus')
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(() => values(page)).toEqual(before)
    await expect(field(page, 'company').locator('input')).toHaveValue('')
    await expect(field(page, 'seats').locator('[role=slider]')).toHaveAttribute('aria-valuenow', '5')
  })

  test('"take me there" finds a Quasar field by data-name and marks it', async ({ page }) => {
    await agent(page, run(directive('start')))
    await open(page, 'quasar')
    await ask(page, 'where does the start date go?')
    await expect(page.locator('form.form [data-name=start][data-agui-highlight]')).toHaveCount(1)
  })

  test('nothing else changes: only the accepted fields move', async ({ page }) => {
    await agent(page, run(card([{ name: 'addons', label: 'Add-ons', value: [{ id: 'support', name: 'Priority support' }], display: 'Priority support', previous: [] }])), run())
    await open(page, 'quasar')
    const before = await values(page)
    await ask(page, 'add priority support')
    await accept(page)
    await expect.poll(async () => (await values(page)).addons).toEqual(['support'])
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'addons') expect(after[k], k).toEqual(before[k])
  })
})

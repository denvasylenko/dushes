/** Vue benchmark stand: PrimeVue 4 components (Select, MultiSelect, DatePicker, Slider, AutoComplete, InputText). */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values, type Change } from './vue-helpers'

const field = (page: Page, name: string) => page.locator(`form.form [data-name="${name}"]`)   // the form's own, not the card's

const FULL: Change[] = [
  { name: 'traveller', label: 'Traveller', value: 'Ann Lee', display: 'Ann Lee', previous: '', previous_display: '' },
  { name: 'destination', label: 'Destination', value: { id: 'rom', name: 'Rome' }, display: 'Rome' },
  { name: 'activities', label: 'Activities', value: [{ id: 'hiking', name: 'Hiking' }, { id: 'food', name: 'Food tours' }], display: 'Hiking, Food tours', previous: [] },
  { name: 'start', label: 'Start date', value: '2026-05-01', display: '1 May 2026' },
  { name: 'budget', label: 'Budget (EUR)', value: 1500, display: '1500', previous: 1000, previous_display: '1000' },
  { name: 'airline', label: 'Airline', value: 'Lufthansa', display: 'Lufthansa', previous: '', previous_display: '' },
]

test.describe('stand: primevue (Select, MultiSelect, DatePicker, Slider, AutoComplete, InputText)', () => {
  test('accepting the card writes Vue state in each component\'s own shape', async ({ page }) => {
    await agent(page, run(card(FULL)), run())
    await open(page, 'primevue')
    await ask(page, 'Ann Lee to Rome on 1 May, hiking and food, 1500 EUR, Lufthansa')
    await accept(page)
    await expect.poll(() => values(page)).toEqual({ traveller: 'Ann Lee', destination: 'rom', activities: ['hiking', 'food'],
                                                     start: '2026-05-01', budget: 1500, airline: 'Lufthansa' })
  })

  test('the components show the values', async ({ page }) => {
    await agent(page, run(card(FULL)), run())
    await open(page, 'primevue')
    await ask(page, 'fill it')
    await accept(page)
    await expect(field(page, 'traveller').locator('input')).toHaveValue('Ann Lee')
    await expect(field(page, 'destination').locator('.p-select-label')).toHaveText('Rome')
    await expect(field(page, 'activities').locator('.p-multiselect-label')).toContainText('Hiking')
    await expect(field(page, 'activities').locator('.p-multiselect-label')).toContainText('Food tours')
    await expect(field(page, 'start').locator('input')).toHaveValue('2026-05-01')
    await expect(field(page, 'budget').locator('.p-slider-handle')).toHaveAttribute('aria-valuenow', '1500')
    await expect(field(page, 'budget').locator('.budget')).toHaveText('1500')
    await expect(field(page, 'airline').locator('input')).toHaveValue('Lufthansa')
  })

  test('Undo puts the Vue state back', async ({ page }) => {
    await agent(page, run(card(FULL)), run())
    await open(page, 'primevue')
    const before = await values(page)
    await ask(page, 'fill it')
    await accept(page)
    await expect.poll(async () => (await values(page)).destination).toBe('rom')
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(() => values(page)).toEqual(before)
    await expect(field(page, 'traveller').locator('input')).toHaveValue('')
    await expect(field(page, 'destination').locator('.p-select-label')).toHaveText('Choose')
  })

  test('"take me there" finds a PrimeVue field by data-name and marks it', async ({ page }) => {
    await agent(page, run(directive('activities')))
    await open(page, 'primevue')
    await ask(page, 'where do I pick activities?')
    await expect(page.locator('form.form [data-name=activities][data-agui-highlight]')).toHaveCount(1)
  })

  test('nothing else changes: only the accepted fields move', async ({ page }) => {
    await agent(page, run(card([{ name: 'destination', label: 'Destination', value: { id: 'osl', name: 'Oslo' }, display: 'Oslo' }])), run())
    await open(page, 'primevue')
    const before = await values(page)
    await ask(page, 'Oslo')
    await accept(page)
    await expect.poll(async () => (await values(page)).destination).toBe('osl')
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'destination') expect(after[k], k).toEqual(before[k])
  })
})

/** Stand of the Vue benchmark: Vuetify components (v-select, multiple, v-date-input, v-slider, v-autocomplete)
 * bound to reactive state. Checks read the Vue state; the component's text proves it re-rendered from it. */
import { expect, test } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values, type Change } from './vue-helpers'

const ALL: Change[] = [
  { name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee', previous: '', previous_display: '' },
  { name: 'country', label: 'Country', value: { id: 'fr', name: 'France' }, display: 'France', previous: '' },
  { name: 'languages', label: 'Languages', value: [{ id: 'en', name: 'English' }, { id: 'it', name: 'Italian' }], display: 'English, Italian', previous: [] },
  { name: 'start', label: 'Start date', value: '2026-12-01', display: '1 Dec 2026', previous: '' },
  { name: 'budget', label: 'Budget (hundreds of EUR)', value: 40, display: '40', previous: 20, previous_display: '20' },
  { name: 'city', label: 'City', value: { id: 'rom', name: 'Rome' }, display: 'Rome', previous: '' },
]
const EMPTY = { name: '', country: '', languages: [], start: '', budget: 20, city: '' }

test.describe('stand: vuetify (Vuetify components on reactive state)', () => {
  test('a card writes every custom field with its shape; the components show it', async ({ page }) => {
    await agent(page, run(card(ALL)), run())
    await open(page, 'vuetify')
    await ask(page, 'Ann Lee, France, English and Italian, from 1 December, budget 40, Rome')
    await accept(page)
    await expect.poll(() => values(page)).toEqual({ name: 'Ann Lee', country: 'fr', languages: ['en', 'it'], start: '2026-12-01', budget: 40, city: 'rom' })
    await expect(page.locator('form [data-name=name] input')).toHaveValue('Ann Lee')
    await expect(page.locator('form .v-select[data-name=country] .v-select__selection-text')).toHaveText('France')
    await expect(page.locator('form .v-select[data-name=languages] .v-chip')).toHaveText(['English', 'Italian'])
    await expect(page.locator('form [data-name=start] input')).toHaveValue('12/01/2026')   // v-date-input shows the en-US keyboard date
    await expect(page.locator('form .v-slider[data-name=budget] [role=slider]')).toHaveAttribute('aria-valuenow', '40')
    await expect(page.locator('form .v-slider[data-name=budget] .v-slider-thumb__label')).toHaveText('40')
    await expect(page.locator('form .v-autocomplete[data-name=city] .v-autocomplete__selection')).toHaveText('Rome')
  })

  test('Undo puts the Vue state back', async ({ page }) => {
    await agent(page, run(card(ALL)), run())
    await open(page, 'vuetify')
    await ask(page, 'fill it all')
    await accept(page)
    await expect.poll(async () => (await values(page)).budget).toBe(40)
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(() => values(page)).toEqual(EMPTY)
    await expect(page.locator('form .v-select[data-name=languages] .v-chip')).toHaveCount(0)
    await expect(page.locator('form .v-slider[data-name=budget] [role=slider]')).toHaveAttribute('aria-valuenow', '20')
  })

  for (const [field, root] of [['country', '.v-select'], ['budget', '.v-slider'], ['languages', '.v-select'], ['start', '.v-input'], ['city', '.v-autocomplete']] as const) {
    test(`"take me there" (${field}) marks the component's wrapper by data-name`, async ({ page }) => {
      await agent(page, run(directive(field)))
      await open(page, 'vuetify')
      await ask(page, `where is ${field}?`)
      await expect(page.locator(`form ${root}[data-name=${field}][data-agui-highlight]`)).toHaveCount(1)
    })
  }

  test('nothing else changes: only the accepted fields move', async ({ page }) => {
    await agent(page, run(card([{ name: 'city', label: 'City', value: { id: 'par', name: 'Paris' }, display: 'Paris', previous: '' }])), run())
    await open(page, 'vuetify')
    const before = await values(page)
    await ask(page, 'Paris')
    await accept(page)
    await expect.poll(async () => (await values(page)).city).toBe('par')
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'city') expect(after[k], k).toEqual(before[k])
  })
})

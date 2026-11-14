/** Vue benchmark stand: a 3-step form with vue-router, one step per route, the state outside the router views. */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values, type Change } from './vue-helpers'

const field = (page: Page, name: string) => page.locator(`form.form [data-name="${name}"]`)   // the form's own, not the card's
const route = (page: Page) => page.evaluate(() => location.hash)

const STEP3: Change[] = [
  { name: 'plan', label: 'Plan', value: { id: 'yearly', name: 'Yearly' }, display: 'Yearly' },
  { name: 'start', label: 'Start date', value: '2027-01-15', display: '15 Jan 2027', previous: '', previous_display: '' },
  { name: 'notes', label: 'Notes', value: 'Gift for my sister', display: 'Gift for my sister', previous: '', previous_display: '' },
]

test.describe('stand: router (one step per route, state outside the views)', () => {
  test('a card for step 3 accepted on step 1 writes the state; step 3 shows it', async ({ page }) => {
    await agent(page, run(card(STEP3)), run())
    await open(page, 'router')
    expect(await route(page)).toBe('#/personal')
    await ask(page, 'Yearly from 15 January, it is a gift for my sister')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ plan: 'yearly', start: '2027-01-15', notes: 'Gift for my sister', name: '' })
    // after writing, the card shows the field it filled (the widget's design): onReveal takes the person to step 3
    await expect.poll(() => route(page)).toBe('#/extras')
    await expect(field(page, 'plan').locator('select')).toHaveValue('yearly')
    await expect(field(page, 'start').locator('input')).toHaveValue('2027-01-15')
    await expect(field(page, 'notes').locator('textarea')).toHaveValue('Gift for my sister')
  })

  test('"take me there" to a step-3 field navigates to its route and marks it', async ({ page }) => {
    await agent(page, run(directive('notes')))
    await open(page, 'router')
    await ask(page, 'where do I add a note?')
    await expect.poll(() => route(page)).toBe('#/extras')
    await expect(page.locator('form.form [data-name=notes][data-agui-highlight]')).toHaveCount(1)
  })

  test('the state survives navigation between steps', async ({ page }) => {
    await agent(page, run(card([{ name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee', previous: '', previous_display: '' }])), run())
    await open(page, 'router')
    await ask(page, 'Ann Lee')
    await accept(page)
    await expect(field(page, 'name').locator('input')).toHaveValue('Ann Lee')
    await page.locator('.steps a', { hasText: 'Address' }).click()
    await field(page, 'city').locator('input').fill('Porto')   // the person types on step 2
    await page.locator('.steps a', { hasText: 'Plan' }).click()
    await page.locator('.steps a', { hasText: 'You' }).click()
    await expect(field(page, 'name').locator('input')).toHaveValue('Ann Lee')
    await page.locator('.steps a', { hasText: 'Address' }).click()
    await expect(field(page, 'city').locator('input')).toHaveValue('Porto')
    expect(await values(page)).toMatchObject({ name: 'Ann Lee', city: 'Porto' })
  })

  test('re-rendering the step (a new key, v-if off and on) keeps the values', async ({ page }) => {
    await agent(page, run(card(STEP3)), run())
    await open(page, 'router')
    await page.locator('.steps a', { hasText: 'Plan' }).click()
    await ask(page, 'fill the plan')
    await accept(page)
    await expect(field(page, 'notes').locator('textarea')).toHaveValue('Gift for my sister')
    await page.locator('.steps .rerender').click()
    await expect(field(page, 'notes').locator('textarea')).toHaveValue('Gift for my sister')
    await expect(field(page, 'plan').locator('select')).toHaveValue('yearly')
    await page.locator('.steps .toggle').click()
    await expect(field(page, 'notes')).toHaveCount(0)
    await page.locator('.steps .toggle').click()
    await expect(field(page, 'notes').locator('textarea')).toHaveValue('Gift for my sister')
    await expect(field(page, 'start').locator('input')).toHaveValue('2027-01-15')
    expect(await values(page)).toMatchObject({ plan: 'yearly', start: '2027-01-15', notes: 'Gift for my sister' })
  })

  test('Undo from another step puts the state back', async ({ page }) => {
    await agent(page, run(card(STEP3)), run())
    await open(page, 'router')
    const before = await values(page)
    await ask(page, 'fill the plan')
    await accept(page)
    await expect.poll(async () => (await values(page)).notes).toBe('Gift for my sister')
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(() => values(page)).toEqual(before)
  })
})

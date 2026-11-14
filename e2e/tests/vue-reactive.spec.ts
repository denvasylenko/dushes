/** Stand 1 of the Vue benchmark: plain Vue state (v-model on reactive and ref, a watcher, computed options). */
import { expect, test } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values } from './vue-helpers'

test.describe('stand: reactive (v-model on reactive and ref, a watcher, computed options)', () => {
  test('accepting the card writes Vue state; watchers run; the region appears and is set', async ({ page }) => {
    await agent(page, run(card([
      { name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee' },
      { name: 'country', label: 'Country', value: { id: 'fr', name: 'France' }, display: 'France' },
      { name: 'region', label: 'Region', value: 'Normandy', display: 'Normandy' },
      { name: 'guests', label: 'Guests', value: 3, display: '3' },
    ])), run())
    await open(page, 'reactive')
    await ask(page, 'Ann Lee, France, Normandy, 3 guests')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ name: 'Ann Lee', country: 'fr', region: 'Normandy', guests: 3, total: 75 })
    expect((await values(page)).watched).toBeGreaterThanOrEqual(1)
    await expect(page.locator('[data-name=region] select')).toHaveValue('Normandy')   // v-if rendered it with the value
  })

  test('a dependent field follows: a new country clears a region it does not have', async ({ page }) => {
    await agent(page,
      run(card([{ name: 'country', label: 'Country', value: { id: 'fr', name: 'France' }, display: 'France' },
                { name: 'region', label: 'Region', value: 'Brittany', display: 'Brittany' }])),
      run(),   // the run that resumes after Accept
      run(card([{ name: 'country', label: 'Country', value: { id: 'de', name: 'Germany' }, display: 'Germany', previous: 'fr', previous_display: 'France' }])),
      run())
    await open(page, 'reactive')
    await ask(page, 'France, Brittany')
    await accept(page)
    await expect.poll(async () => (await values(page)).region).toBe('Brittany')
    await ask(page, 'Actually Germany')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ country: 'de', region: '' })
  })

  test('Undo puts the Vue state back', async ({ page }) => {
    await agent(page, run(card([{ name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee', previous: '', previous_display: '' }])), run())
    await open(page, 'reactive')
    await ask(page, 'My name is Ann Lee')
    await accept(page)
    await expect.poll(async () => (await values(page)).name).toBe('Ann Lee')
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(async () => (await values(page)).name).toBe('')
  })

  test('"take me there" finds the field by data-name and marks it', async ({ page }) => {
    await agent(page, run(directive('email')))
    await open(page, 'reactive')
    await ask(page, 'where does my email go?')
    await expect(page.locator('[data-name=email][data-agui-highlight]')).toHaveCount(1)
  })

  test('nothing else changes: only the accepted fields move', async ({ page }) => {
    await agent(page, run(card([{ name: 'email', label: 'Email', value: 'ann@example.com', display: 'ann@example.com' }])), run())
    await open(page, 'reactive')
    const before = await values(page)
    await ask(page, 'ann@example.com')
    await accept(page)
    await expect.poll(async () => (await values(page)).email).toBe('ann@example.com')
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'email') expect(after[k], k).toEqual(before[k])
  })
})

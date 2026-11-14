/** Stand of the Vue benchmark: the form lives in a Pinia store (state, a getter for the regions, an action for the price). */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, DIST, open, run, values } from './vue-helpers'

type Body = { state?: { config?: { props?: Record<string, Record<string, unknown>> } } }
const props = (b: Record<string, unknown> | undefined) => (b as Body | undefined)?.state?.config?.props ?? {}
const regionShown = (page: Page) => page.locator('.form [data-name=region] select')

test.describe('stand: pinia (the store is the source; a getter, a watcher and an action)', () => {
  // the stand passes with a store-aware access() (verified); remove this once the reference adapter has it
  test('accepting the card writes the store; the action recalculates the price', async ({ page }) => {
    await agent(page, run(card([
      { name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee' },
      { name: 'country', label: 'Country', value: { id: 'fr', name: 'France' }, display: 'France' },
      { name: 'region', label: 'Region', value: 'Normandy', display: 'Normandy' },
      { name: 'plan', label: 'Plan', value: { id: 'plus', name: 'Plus' }, display: 'Plus' },
      { name: 'guests', label: 'Guests', value: 3, display: '3' },
    ])), run())
    await open(page, 'pinia')
    const before = (await values(page)).recalcs as number
    await ask(page, 'Ann Lee, Normandy in France, Plus for 3')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ name: 'Ann Lee', country: 'fr', region: 'Normandy', plan: 'plus', guests: 3, price: 105 })
    expect((await values(page)).recalcs).toBeGreaterThan(before)
    await expect(regionShown(page)).toHaveValue('Normandy')   // v-model on the store rendered it
    await expect(page.locator('.form [data-name=plan] input[value=plus]')).toBeChecked()
  })

  test('the getter-dependent options follow the country, and the watcher clears a region the new country lacks', async ({ page }) => {
    const bodies = await agent(page,
      run(card([{ name: 'country', label: 'Country', value: { id: 'it', name: 'Italy' }, display: 'Italy' },
                { name: 'region', label: 'Region', value: 'Tuscany', display: 'Tuscany' }])),
      run(),
      run(card([{ name: 'country', label: 'Country', value: { id: 'de', name: 'Germany' }, display: 'Germany', previous: 'it', previous_display: 'Italy' }])),
      run())
    await open(page, 'pinia')
    await ask(page, 'Tuscany, Italy')
    await accept(page)
    expect(props(bodies[0]).region?.visible).toBe(false)   // before the card: no country, the region is hidden
    await expect.poll(() => values(page)).toMatchObject({ country: 'it', region: 'Tuscany', regions: ['Lazio', 'Tuscany'] })
    expect(props(bodies[1]).region).toMatchObject({ visible: true, options: [{ id: 'Lazio', name: 'Lazio' }, { id: 'Tuscany', name: 'Tuscany' }] })
    await ask(page, 'Actually Germany')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ country: 'de', region: '', regions: ['Bavaria', 'Berlin', 'Hesse'] })
    expect((props(bodies[3]).region?.options as { id: string }[]).map((o) => o.id)).toEqual(['Bavaria', 'Berlin', 'Hesse'])
  })

  test('Undo puts the store back, and the action runs again', async ({ page }) => {
    await agent(page, run(card([{ name: 'guests', label: 'Guests', value: 4, display: '4', previous: 1, previous_display: '1' }])), run())
    await open(page, 'pinia')
    await ask(page, '4 guests')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ guests: 4, price: 80 })
    await page.locator('agui-chat .card .ok-line .btn').first().click()   // Undo
    await expect.poll(() => values(page)).toMatchObject({ guests: 1, price: 20 })
    await expect(page.locator('.form [data-name=guests] input')).toHaveValue('1')
  })

  test('"take me there" finds the field by data-name and marks it', async ({ page }) => {
    await agent(page, run(directive('insurance')))
    await open(page, 'pinia')
    await ask(page, 'where is the insurance?')
    await expect(page.locator('.form [data-name=insurance][data-agui-highlight]')).toHaveCount(1)
  })

  test('nothing else changes: only the accepted fields move in the store', async ({ page }) => {
    await agent(page, run(card([{ name: 'email', label: 'Email', value: 'ann@example.com', display: 'ann@example.com' }])), run())
    await open(page, 'pinia')
    const before = await values(page)
    await ask(page, 'ann@example.com')
    await accept(page)
    await expect.poll(async () => (await values(page)).email).toBe('ann@example.com')
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'email') expect(after[k], k).toEqual(before[k])
  })
})

/** Stand of the Vue benchmark: Vuelidate 2 (required, numeric + between, sameAs, requiredIf for the company name). */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values } from './vue-helpers'

type Body = { state?: { config?: { props?: Record<string, Record<string, unknown>> } } }
const props = (b: Record<string, unknown> | undefined) => (b as Body | undefined)?.state?.config?.props ?? {}
const errors = (page: Page) => page.evaluate(() => (window as unknown as { __stand: { errors: () => Record<string, string> } }).__stand.errors())

test.describe('stand: vuelidate ($validate() after every write, $errors in the config)', () => {
  test('seats out of range leave an error in the form and in the next run; a number in range clears it', async ({ page }) => {
    const bodies = await agent(page,
      run(card([{ name: 'seats', label: 'Seats', value: 80, display: '80' }])),
      run(),
      run(card([{ name: 'seats', label: 'Seats', value: 12, display: '12', previous: 80, previous_display: '80' }])),
      run())
    await open(page, 'vuelidate')
    await ask(page, '80 seats')
    await accept(page)
    await expect.poll(async () => (await errors(page)).seats).toBe('From 1 to 50 seats')
    expect(props(bodies[1]).seats?.error).toBe('From 1 to 50 seats')
    await expect(page.locator('.form [data-name=seats] input')).toHaveValue('80')
    await ask(page, 'make it 12')
    await accept(page)
    await expect.poll(async () => (await errors(page)).seats).toBeUndefined()
    expect(props(bodies[3]).seats?.error).toBeUndefined()
    expect((await values(page)).seats).toBe(12)
  })

  test('sameAs: a different confirmation is an error; the same one clears it', async ({ page }) => {
    const bodies = await agent(page,
      run(card([{ name: 'password', label: 'Password', value: 'blue-kite-7', display: 'blue-kite-7' },
                { name: 'confirm', label: 'Repeat the password', value: 'blue-kite-8', display: 'blue-kite-8' }])),
      run(),
      run(card([{ name: 'confirm', label: 'Repeat the password', value: 'blue-kite-7', display: 'blue-kite-7', previous: 'blue-kite-8', previous_display: 'blue-kite-8' }])),
      run())
    await open(page, 'vuelidate')
    await ask(page, 'password blue-kite-7, again blue-kite-8')
    await accept(page)
    await expect.poll(async () => (await errors(page)).confirm).toBe('The passwords differ')
    expect(props(bodies[1]).confirm?.error).toBe('The passwords differ')
    await ask(page, 'the second is blue-kite-7')
    await accept(page)
    await expect.poll(async () => (await errors(page)).confirm).toBeUndefined()
    expect(props(bodies[3]).confirm?.error).toBeUndefined()
    expect(await values(page)).toMatchObject({ password: 'blue-kite-7', confirm: 'blue-kite-7' })
  })

  test('a dependent rule: the company name is required only for a business account', async ({ page }) => {
    const bodies = await agent(page,
      run(card([{ name: 'business', label: 'This is a business account', value: true, display: 'Yes' }])),
      run(),
      run(card([{ name: 'company', label: 'Company name', value: 'Acme Ltd', display: 'Acme Ltd' }])),
      run())
    await open(page, 'vuelidate')
    await ask(page, 'it is for my business')
    await accept(page)
    expect(props(bodies[0]).company).toMatchObject({ visible: false, required: false })   // before the card
    await expect.poll(async () => (await errors(page)).company).toBe('Enter the company name')
    expect(props(bodies[1]).company).toMatchObject({ visible: true, required: true, error: 'Enter the company name' })
    await expect(page.locator('.form [data-name=company] input')).toHaveCount(1)   // v-if showed it
    await ask(page, 'Acme Ltd')
    await accept(page)
    await expect.poll(async () => (await errors(page)).company).toBeUndefined()
    expect(props(bodies[3]).company?.error).toBeUndefined()
    expect(await values(page)).toMatchObject({ business: true, company: 'Acme Ltd' })
    await expect(page.locator('.form [data-name=company] input')).toHaveValue('Acme Ltd')
  })

  test('"take me there" finds the field by data-name and marks it', async ({ page }) => {
    await agent(page, run(directive('seats')))
    await open(page, 'vuelidate')
    await ask(page, 'where do I set the seats?')
    await expect(page.locator('.form [data-name=seats][data-agui-highlight]')).toHaveCount(1)
  })

  test('nothing else changes: only the accepted fields move', async ({ page }) => {
    await agent(page, run(card([{ name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee' }])), run())
    await open(page, 'vuelidate')
    const before = await values(page)
    await ask(page, 'Ann Lee')
    await accept(page)
    await expect.poll(async () => (await values(page)).name).toBe('Ann Lee')
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'name') expect(after[k], k).toEqual(before[k])
  })
})

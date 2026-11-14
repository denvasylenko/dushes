/** Stand of the Vue benchmark: VeeValidate 4 (useForm + useField, rules: required, email, at least 18 from a date). */
import { expect, test, type Page } from '@playwright/test'

import { accept, agent, ask, card, directive, open, run, values } from './vue-helpers'

type Body = { state?: { config?: { props?: Record<string, Record<string, unknown>> } } }
const props = (b: Record<string, unknown> | undefined) => (b as Body | undefined)?.state?.config?.props ?? {}
const errors = (page: Page) => page.evaluate(() => (window as unknown as { __stand: { errors: () => Record<string, string> } }).__stand.errors())
/** An ISO date `years` years before today (minus a day for "already had the birthday"). */
const yearsAgo = (years: number, dayShift = -1) => {
  const d = new Date(); d.setFullYear(d.getFullYear() - years); d.setDate(d.getDate() + dayShift)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

test.describe('stand: veevalidate (useForm + useField, validate() after every write, errors in the config)', () => {
  test('an invalid email leaves an error in the form and in the next run; a valid one clears it', async ({ page }) => {
    const bodies = await agent(page,
      run(card([{ name: 'email', label: 'Email', value: 'ann@example', display: 'ann@example' }])),
      run(),
      run(card([{ name: 'email', label: 'Email', value: 'ann@example.com', display: 'ann@example.com', previous: 'ann@example', previous_display: 'ann@example' }])),
      run())
    await open(page, 'veevalidate')
    await ask(page, 'ann@example')
    await accept(page)
    await expect.poll(async () => (await errors(page)).email).toBe('Enter a valid email')
    expect(props(bodies[1]).email?.error).toBe('Enter a valid email')   // the resumed run carries the library's error
    await expect(page.locator('.form [data-name=email] input')).toHaveValue('ann@example')   // v-model shows it
    await expect(page.locator('.form [data-name=email] .err')).toHaveText('Enter a valid email')
    await ask(page, 'Sorry, ann@example.com')
    await accept(page)
    await expect.poll(async () => (await errors(page)).email).toBeUndefined()
    expect(props(bodies[3]).email?.error).toBeUndefined()
    expect((await values(page)).email).toBe('ann@example.com')
    await expect(page.locator('.form [data-name=email] input')).toHaveValue('ann@example.com')
  })

  test('the age rule: under 18 is an error in the next run, 18 or older clears it', async ({ page }) => {
    const young = yearsAgo(17), adult = yearsAgo(30)
    const bodies = await agent(page,
      run(card([{ name: 'birthDate', label: 'Birth date', value: young, display: young }])),
      run(),
      run(card([{ name: 'birthDate', label: 'Birth date', value: adult, display: adult, previous: young, previous_display: young }])),
      run())
    await open(page, 'veevalidate')
    await ask(page, `born ${young}`)
    await accept(page)
    await expect.poll(async () => (await errors(page)).birthDate).toBe('You must be at least 18')
    expect(props(bodies[1]).birthDate?.error).toBe('You must be at least 18')
    await expect(page.locator('.form [data-name=birthDate] input')).toHaveValue(young)
    await ask(page, `no, ${adult}`)
    await accept(page)
    await expect.poll(async () => (await errors(page)).birthDate).toBeUndefined()
    expect(props(bodies[3]).birthDate?.error).toBeUndefined()
    expect((await values(page)).birthDate).toBe(adult)
  })

  test('a valid card updates the v-model state with no errors on its fields', async ({ page }) => {
    const bodies = await agent(page, run(card([
      { name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee' },
      { name: 'email', label: 'Email', value: 'ann@example.com', display: 'ann@example.com' },
      { name: 'newsletter', label: 'Send me the newsletter', value: true, display: 'Yes' },
    ])), run())
    await open(page, 'veevalidate')
    await ask(page, 'Ann Lee, ann@example.com, newsletter yes')
    await accept(page)
    await expect.poll(() => values(page)).toMatchObject({ name: 'Ann Lee', email: 'ann@example.com', newsletter: true })
    const e = await errors(page)
    expect([e.name, e.email]).toEqual([undefined, undefined])
    expect(props(bodies[1]).birthDate?.error).toBe('Enter your birth date')   // validate() ran over the whole form
    await expect(page.locator('.form [data-name=name] input')).toHaveValue('Ann Lee')
    await expect(page.locator('.form [data-name=newsletter] input')).toBeChecked()
  })

  test('"take me there" finds the field by data-name and marks it', async ({ page }) => {
    await agent(page, run(directive('birthDate')))
    await open(page, 'veevalidate')
    await ask(page, 'where is my birth date?')
    await expect(page.locator('.form [data-name=birthDate][data-agui-highlight]')).toHaveCount(1)
  })

  test('nothing else changes: only the accepted fields move', async ({ page }) => {
    await agent(page, run(card([{ name: 'name', label: 'Full name', value: 'Ann Lee', display: 'Ann Lee' }])), run())
    await open(page, 'veevalidate')
    const before = await values(page)
    await ask(page, 'Ann Lee')
    await accept(page)
    await expect.poll(async () => (await values(page)).name).toBe('Ann Lee')
    const after = await values(page)
    for (const k of Object.keys(before)) if (k !== 'name') expect(after[k], k).toEqual(before[k])
  })
})

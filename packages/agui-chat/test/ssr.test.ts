// @vitest-environment node
import { describe, expect, it } from 'vitest'

// Server rendering (Nuxt, Next, Astro) imports the package where there is no DOM: no entry may throw on import.
describe('importing on the server', () => {
  it('every entry imports without a DOM', async () => {
    expect(typeof globalThis.HTMLElement).toBe('undefined')
    for (const load of [() => import('../src/index'), () => import('../src/formguide/index'), () => import('../src/highlight'),
      () => import('../src/react'), () => import('../src/rhf')]) await expect(load()).resolves.toBeTruthy()
  }, 30_000)   // five cold imports: slow on a busy machine
})

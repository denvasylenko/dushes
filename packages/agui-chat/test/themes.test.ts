import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { defineTheme, themeCss, themes, tokenName } from '../src/themes'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))

/** The theme's CSS as the element holds it (a constructed sheet, or a <style> fallback). */
function themeText(el: AguiChatElement): string {
  const root = el.shadowRoot!
  const sheets = root.adoptedStyleSheets ?? []
  if (sheets.length > 1) return [...sheets[1].cssRules].map((r) => r.cssText).join('\n')
  const styles = root.querySelectorAll('style')
  return styles[styles.length - 1]?.textContent ?? ''
}

async function mount(attrs: Record<string, string> = {}): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat')
  for (const [k, v] of Object.entries({ mode: 'inline', 'persist-thread': 'off', ...attrs })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  return el
}

let dark = false
const listeners = new Set<() => void>()
beforeEach(() => {
  document.body.innerHTML = ''
  dark = false
  listeners.clear()
  vi.spyOn(console, 'warn').mockImplementation(() => {})
  vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 404 })))
  vi.stubGlobal('matchMedia', (q: string) => ({
    get matches() { return q.includes('dark') ? dark : q.includes('pointer: fine') },
    media: q,
    addEventListener: (_: string, f: () => void) => listeners.add(f),
    removeEventListener: (_: string, f: () => void) => listeners.delete(f),
  }))
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('themes', () => {
  it('ships default and contrast, and normalises token keys', () => {
    expect(themes()).toEqual(expect.arrayContaining(['default', 'contrast']))
    expect(tokenName('accent')).toBe('--agui-accent')
    expect(tokenName('--accent')).toBe('--agui-accent')
    expect(tokenName('--agui-radius-sm')).toBe('--agui-radius-sm')
    expect(tokenName('colour')).toBeNull()
  })

  it('writes both schemes, drops unsafe values and unknown keys', () => {
    const css = themeCss({ tokens: { accent: '#0a7f6f', radius: '4px', colour: 'red', bg: 'red; } * { display: none' }, dark: { accent: '#4fd1c1' } })
    const [light, darkRule] = css.split('\n')
    expect(light).toContain('--agui-accent: #0a7f6f;')
    expect(light).toContain('--agui-radius: 4px;')
    expect(darkRule.startsWith(':host(.dark)')).toBe(true)
    expect(darkRule.indexOf('--agui-accent: #4fd1c1')).toBeGreaterThan(darkRule.indexOf('--agui-accent: #0a7f6f'))   // dark wins
    expect(css).not.toContain('display: none')
    expect(css).not.toContain('colour')
  })

  it('merges extends, parents first', () => {
    defineTheme('base-x', { tokens: { accent: '#111', radius: '2px' }, css: '.chip { font-weight: 600 }' })
    const css = themeCss({ extends: 'base-x', tokens: { accent: '#222' }, css: '.card { border-width: 2px }' })
    expect(css).toContain('--agui-radius: 2px')
    expect(css.indexOf('#222')).toBeGreaterThan(css.indexOf('#111'))
    expect(css.indexOf('.card')).toBeGreaterThan(css.indexOf('.chip'))
  })
})

describe('<agui-chat> theme and scheme', () => {
  it('applies a named theme and reflects it on the host', async () => {
    defineTheme('acme', { tokens: { accent: '#0a7f6f' }, dark: { accent: '#4fd1c1' } })
    const el = await mount({ theme: 'acme' })
    expect(el.dataset.theme).toBe('acme')
    expect(el.dataset.scheme).toBe('light')
    expect(themeText(el)).toContain('#0a7f6f')
    el.setAttribute('scheme', 'dark')
    expect(el.dataset.scheme).toBe('dark')
    expect(el.classList.contains('dark')).toBe(true)
  })

  it('takes a theme object and switches to a theme defined later', async () => {
    const el = await mount()
    el.options = { theme: { tokens: { radius: '0' } } }
    expect(el.dataset.theme).toBe('custom')
    expect(themeText(el)).toContain('--agui-radius: 0')

    el.options = { theme: 'late' }
    expect(el.dataset.theme).toBe('default')                  // unknown for now
    defineTheme('late', { tokens: { accent: '#abcdef' } })
    expect(el.dataset.theme).toBe('late')
    expect(themeText(el)).toContain('#abcdef')
  })

  it('follows the system scheme live with auto', async () => {
    const el = await mount({ scheme: 'auto' })
    expect(el.dataset.scheme).toBe('light')
    dark = true
    listeners.forEach((f) => f())
    expect(el.dataset.scheme).toBe('dark')
    el.remove()
    expect(listeners.size).toBe(0)                            // no listener left behind
  })

  it('still reads theme="dark" as the scheme', async () => {
    const el = await mount({ theme: 'dark' })
    expect(el.dataset.scheme).toBe('dark')
    expect(el.dataset.theme).toBe('default')
    el.setAttribute('theme', 'light')
    expect(el.dataset.scheme).toBe('light')
  })
})

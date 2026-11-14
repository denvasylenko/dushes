import { afterEach, describe, expect, it, vi } from 'vitest'
import { highlightField, HIGHLIGHT_CSS } from '../src/highlight'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
afterEach(() => { document.body.innerHTML = ''; vi.unstubAllGlobals() })

describe('the field highlight', () => {
  it('finds a field by data-name (an input rings its box), marks it, ends by itself, and restarts on a second call', async () => {
    document.body.innerHTML = '<div data-name="amount" style="--agui-highlight-ms: 80"><input name="amount"></div>'
    const box = document.querySelector<HTMLElement>('[data-name="amount"]')!
    highlightField(document.querySelector('input')!)
    expect(box.dataset.aguiHighlight).toBe('changed')
    expect(box.dataset.aguiHighlightStyle).toBe('ring')
    await tick(50)
    highlightField('amount', { style: 'glow' })                          // again: starts over
    await tick(50)
    expect(box.dataset.aguiHighlightStyle).toBe('glow')                 // the first timer did not end the second
    await tick(60)
    expect(box.dataset.aguiHighlightOut).toBe('')                       // it fades out
    await tick(350)
    expect(box.dataset.aguiHighlight).toBeUndefined()
  })

  it('a name with no data-name falls back to [name]; cancel ends it at once; look scrolls and shows the hint', async () => {
    document.body.innerHTML = '<input name="email"><div data-name="phone"><input></div>'
    const cancel = highlightField('email')
    const input = document.querySelector<HTMLInputElement>('input[name=email]')!
    expect(input.dataset.aguiHighlight).toBe('changed')
    cancel()
    expect(input.dataset.aguiHighlight).toBeUndefined()
    const phone = document.querySelector<HTMLElement>('[data-name=phone]')!
    phone.scrollIntoView = vi.fn()
    highlightField('phone', { kind: 'look', hint: 'Ten digits' })
    expect(phone.dataset.aguiHighlight).toBe('look')
    expect(phone.scrollIntoView).toHaveBeenCalled()
    await tick(400)
    expect(document.querySelector('[data-formguide-hint]')!.textContent).toBe('Ten digits')
  })

  it('shared tokens first, the widget variables next, the current look last; a steady ring with reduced motion', () => {
    expect(HIGHLIGHT_CSS).toContain('var(--hf-ok, var(--agui-highlight-color, #34c759))')
    expect(HIGHLIGHT_CSS).toContain('var(--hf-hl-w, var(--agui-highlight-width, 3px))')
    expect(HIGHLIGHT_CSS).toContain('var(--hf-hl-mix, var(--agui-highlight-mix, 45%))')
    expect(HIGHLIGHT_CSS).toMatch(/prefers-reduced-motion: reduce\) \{ \[data-agui-highlight\] \{ animation: none/)
    expect(highlightField('nothing-here')).toBeTypeOf('function')        // a missing field is no error
  })

  it('the look-here hint is a pill inside the field (its own corner) and leaves with the ring', async () => {
    document.body.innerHTML = '<div data-name="term" style="--agui-highlight-ms: 600"><input></div>'
    const box = document.querySelector<HTMLElement>('[data-name=term]')!
    box.scrollIntoView = vi.fn()
    box.getBoundingClientRect = () => ({ width: 300, height: 64, top: 0, left: 0, right: 300, bottom: 64, x: 0, y: 0, toJSON() {} }) as DOMRect
    highlightField('term', { kind: 'look', hint: 'Choose 12 to 60 months' })
    await tick(400)
    const pill = box.querySelector<HTMLElement>('.agui-hl-hint')!
    expect(pill.textContent).toBe('Choose 12 to 60 months')
    expect(pill.classList.contains('below')).toBe(false)
    expect(box.style.position).toBe('relative')
    ;(document.activeElement as HTMLElement | null)?.blur()
    await tick(300)                                                        // the ring ends at 600 ms, then both fade
    expect(pill.classList.contains('out')).toBe(true)
    expect(box.dataset.aguiHighlightOut).toBe('')
    await tick(400)
    expect(box.querySelector('.agui-hl-hint')).toBeNull()
    expect(box.dataset.aguiHighlight).toBeUndefined()
    expect(box.style.position).toBe('')                                  // the field is left as it was
  })

  it('<agui-highlight name> is a box with data-name', async () => {
    document.body.innerHTML = '<agui-highlight name="city"><input></agui-highlight>'
    await tick()
    expect(document.querySelector<HTMLElement>('agui-highlight')!.dataset.name).toBe('city')
  })
})

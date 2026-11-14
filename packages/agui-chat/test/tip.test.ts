import { afterEach, describe, expect, it, vi } from 'vitest'
import { ariaKeys, attachTip, keyLabel } from '../src/tip'

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); document.body.innerHTML = '' })

describe('shortcut tooltips', () => {
  it('writes keys per platform: symbols on a Mac, words elsewhere', () => {
    expect(['Mod', 'Alt', 'Shift', 'Enter', 'D'].map((k) => keyLabel(k, true))).toEqual(['⌘', '⌥', '⇧', '↵', 'D'])
    expect(['Mod', 'Alt', 'Shift', 'Enter', 'D'].map((k) => keyLabel(k, false))).toEqual(['Ctrl', 'Alt', 'Shift', 'Enter', 'D'])
    expect(ariaKeys(['Mod', 'D'], true)).toBe('Meta+D')
    expect(ariaKeys(['Shift', 'Enter'], false)).toBe('Shift+Enter')
  })

  it('shows after a moment of mouse hover with one row per action and its keys; never on a touch screen', () => {
    vi.useFakeTimers()
    const host = document.createElement('div'), b = document.createElement('button')
    host.append(b); document.body.append(host)
    attachTip(b, host, () => [{ label: 'Send', keys: ['Enter'] }, { label: 'New line', keys: ['Shift', 'Enter'] }])
    b.dispatchEvent(new PointerEvent('pointerenter', { pointerType: 'mouse' }))
    expect(host.querySelector('.tip')).toBeNull()                 // not at once
    vi.advanceTimersByTime(520)
    const tip = host.querySelector('.tip') as HTMLElement
    expect(tip.hidden).toBe(false)
    expect([...tip.querySelectorAll('.tip-row')].map((r) => r.querySelector('span')!.textContent)).toEqual(['Send', 'New line'])
    expect(tip.querySelectorAll('.tip-row')[1].querySelectorAll('kbd')).toHaveLength(2)
    expect(b.getAttribute('aria-describedby')).toBe(tip.id)
    b.dispatchEvent(new PointerEvent('pointerleave'))
    expect(tip.hidden).toBe(true)
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: q === '(hover: none)' }))
    b.dispatchEvent(new PointerEvent('pointerenter', { pointerType: 'mouse' }))
    vi.advanceTimersByTime(520)
    expect(tip.hidden).toBe(true)
  })
})

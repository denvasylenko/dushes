/**
 * A tooltip with keyboard shortcuts, as on macOS and in the Claude app: a small dark plate over a button, one row per
 * action, the keys on the right as little key caps ("Send  ↵", "New line  ⇧ ↵"). It shows after ~500 ms of hover with a
 * mouse, at once on keyboard focus, and never on a touch screen (no keys there). Keys are written once, platform-free
 * ('Mod', 'Alt', 'Shift', 'Ctrl', 'Enter', 'Esc' or a letter) and shown per platform: ⌘ ⌥ ⇧ ⌃ ↵ on a Mac, Ctrl, Alt,
 * Shift, Enter as words elsewhere.
 *
 * Self-contained (no chat state) so it can move to a shared component library: attachTip(button, host, rows).
 */

export interface TipRow { label: string; keys?: string[] }

import { isMac, keyLabel } from './keys'
import { TIP_CSS } from './tip-css'

export { ariaKeys, isMac, keyLabel } from './keys'

const tips = new WeakMap<Node, HTMLElement>()
let shown: { el: HTMLElement; host: HTMLElement; timer?: ReturnType<typeof setTimeout> } | null = null

/** No hover and no keys on a touch screen. */
const touchOnly = (): boolean => !!globalThis.matchMedia?.('(hover: none)').matches

const styled = new WeakSet<Node>()
/** The tooltip's styles in the root it shows in (a shadow root gets them once; the page needs a <style> of its own). */
function style(host: HTMLElement): void {
  const root = host.getRootNode()
  if (styled.has(root) || !(root instanceof ShadowRoot)) return
  styled.add(root)
  try { const sh = new CSSStyleSheet(); sh.replaceSync(TIP_CSS); root.adoptedStyleSheets = [...root.adoptedStyleSheets, sh] }
  catch { const el = document.createElement('style'); el.textContent = TIP_CSS; root.append(el) }
}

function plate(host: HTMLElement): HTMLElement {
  style(host)
  let t = tips.get(host)
  if (!t) {
    t = document.createElement('div')
    t.className = 'tip'
    t.setAttribute('role', 'tooltip')
    t.setAttribute('part', 'tooltip')
    t.id = `tip-${Math.random().toString(36).slice(2, 8)}`
    t.hidden = true
    host.append(t)
    tips.set(host, t)
  }
  return t
}

function hide(): void {
  if (!shown) return
  clearTimeout(shown.timer)
  const t = tips.get(shown.host)
  if (t) t.hidden = true
  shown = null
}

/**
 * Give `button` a shortcut tooltip drawn in `host` (a positioned box that contains the button, e.g. the chat panel).
 * `rows` is read each time it shows, so it can follow the button's state (Send / Stop). Returns a function that
 * removes it. `enabled()` lets a host turn tooltips off.
 */
export function attachTip(button: HTMLElement, host: HTMLElement, rows: () => TipRow[], enabled: () => boolean = () => true): () => void {
  const show = (): void => {
    if (!enabled() || touchOnly() || !button.isConnected) return
    const list = rows().filter((r) => r.label)
    if (!list.length) return
    const t = plate(host)
    const mac = isMac()
    t.replaceChildren(...list.map((r) => {
      const row = document.createElement('div')
      row.className = 'tip-row'
      const label = document.createElement('span')
      label.textContent = r.label
      row.append(label)
      if (r.keys?.length) {
        const keys = document.createElement('span')
        keys.className = 'tip-keys'
        for (const k of r.keys) { const kbd = document.createElement('kbd'); kbd.textContent = keyLabel(k, mac); keys.append(kbd) }
        row.append(keys)
      }
      return row
    }))
    t.hidden = false
    const b = button.getBoundingClientRect(), h = host.getBoundingClientRect()
    const w = t.offsetWidth, ht = t.offsetHeight
    let top = b.top - h.top - ht - 8
    if (top < 4) top = b.bottom - h.top + 8   // no room above: under the button
    t.style.left = `${Math.max(6, Math.min(h.width - w - 6, b.left - h.left + b.width / 2 - w / 2))}px`
    t.style.top = `${top}px`
    button.setAttribute('aria-describedby', t.id)
  }
  const later = (e: PointerEvent): void => {
    if (e.pointerType !== 'mouse') return
    hide()
    shown = { el: button, host, timer: setTimeout(show, 500) }   // as on macOS: a moment of hover first
  }
  const now = (): void => { if (button.matches(':focus-visible')) { hide(); shown = { el: button, host }; show() } }   // keyboard: at once
  const off = (): void => { hide(); button.removeAttribute('aria-describedby') }
  const esc = (e: KeyboardEvent): void => { if (e.key === 'Escape' && shown?.el === button) off() }
  button.addEventListener('pointerenter', later)
  button.addEventListener('pointerleave', off)
  button.addEventListener('pointerdown', off)
  button.addEventListener('focus', now)
  button.addEventListener('blur', off)
  button.addEventListener('keydown', esc)
  return () => {
    off()
    button.removeEventListener('pointerenter', later); button.removeEventListener('pointerleave', off); button.removeEventListener('pointerdown', off)
    button.removeEventListener('focus', now); button.removeEventListener('blur', off); button.removeEventListener('keydown', esc)
  }
}

export { TIP_CSS }

// the one-script build: agui-chat.tip.js registers it on window.AguiChat
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.attachTip = attachTip

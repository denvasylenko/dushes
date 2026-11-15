/**
 * A small menu that opens from a button, as the + menu in the Claude app or a pull-down menu on iOS: a rounded plate
 * above the button, one row per item (an icon, a label, a shortcut or a chevron on the right). A row with `items`
 * opens them in place, with a way back. Arrows move, Enter and Space choose, Esc and a tap outside close it and give
 * the focus back to the button. Rows are 44 px on a touch screen. Loaded with the tooltip (agui-chat.tip.js), the first
 * time a menu opens; its styles are in tip-css.ts.
 *
 * Self-contained (no chat state): openMenu(button, host, items, onPick).
 */
import { isMac, keyLabel } from './keys'
import { adoptTipCss } from './tip-css'

export interface MenuItem {
  id: string
  label: string
  /** An SVG path on a 24 grid (stroke), or nothing. */
  icon?: string
  /** A second, smaller line (what a command does). */
  hint?: string
  /** A shortcut, written platform-free ('Mod', 'Shift', a letter). Shown with a mouse only. */
  keys?: string[]
  /** A list that opens in place of this one (commands). */
  items?: MenuItem[]
}

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, text?: string): HTMLElementTagNameMap[K] => {
  const e = document.createElement(tag); e.className = cls
  if (text !== undefined) e.textContent = text
  return e
}
const svg = (d: string): string => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d.replace(/[^\w\s.,-]/g, '')}"/></svg>`

let closeOpen: (() => void) | null = null
let openFor: HTMLElement | null = null

/** What the chat's + offers: what is on, the host's commands and its own rows. */
export interface ChatMenu {
  /** The chat's file picker when attachments are on: "Add files or photos" opens it, "Take a photo" asks it for the camera. */
  files: HTMLInputElement | false
  /** What the picker accepts as a file (the camera row sets image/* for its own pick, then this comes back). */
  accept?: string
  touch: boolean; commands?: MenuItem[]; more?: MenuItem[]; t: (key: string) => string
}

/** The chat's + menu: "Add files or photos" (and "Take a photo" on a phone) when attachments are on, "Commands" when
 *  the host has any, then the host's own rows. */
export const chatItems = (c: ChatMenu): MenuItem[] => [
  ...(c.files ? [{ id: 'files', label: c.t('attach'), icon: 'M20 11.5l-8 8a5 5 0 0 1-7-7l8.5-8.5a3.3 3.3 0 0 1 4.7 4.7L10 16.9a1.7 1.7 0 0 1-2.4-2.4l7.4-7.4' }] : []),
  ...(c.files && c.touch ? [{ id: 'photo', label: c.t('takePhoto'), icon: 'M4 8h3l1.5-2h7L17 8h3v11H4zM12 16.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6' }] : []),
  ...(c.commands?.length ? [{ id: 'commands', label: c.t('commands'), icon: 'M5 5h14v14H5zM14 8l-4 8', items: c.commands }] : []),
  ...(c.more ?? []),
]

/**
 * Open `items` over `button`, inside `host` (a positioned box that contains the button). `onPick` gets the chosen item
 * (never one that has `items`). `start` opens a submenu at once (the id of an item with `items`: "/" in the composer).
 * Returns a function that closes it; opening it again while open closes it (the button toggles).
 */
export function openMenu(button: HTMLElement, host: HTMLElement, from: MenuItem[] | ChatMenu, onPick: (item: MenuItem) => void, start?: string): () => void {
  const items = Array.isArray(from) ? from : chatItems(from)
  const picker = Array.isArray(from) ? false : from.files, accept = Array.isArray(from) ? '' : from.accept ?? ''
  const pick = (it: MenuItem): void => {
    if (!picker || (it.id !== 'files' && it.id !== 'photo')) return onPick(it)
    const photo = it.id === 'photo'   // the camera is the same picker, asked for a photo; the next pick is a file again
    picker.toggleAttribute('capture', photo)
    if (photo || accept) picker.accept = photo ? 'image/*' : accept; else picker.removeAttribute('accept')
    picker.click()
  }
  const mine = openFor === button   // the button of an open menu closes it (a toggle)
  closeOpen?.()
  if (mine) return () => {}
  const menu = el('div', 'menu')
  menu.setAttribute('role', 'menu'); menu.setAttribute('part', 'menu')
  const fine = !globalThis.matchMedia?.('(hover: none)').matches
  const rows = (): HTMLElement[] => [...menu.querySelectorAll<HTMLElement>('[role=menuitem]')]
  const close = (focus = true): void => {
    if (!menu.isConnected) return
    menu.remove(); closeOpen = null; openFor = null
    button.setAttribute('aria-expanded', 'false')
    document.removeEventListener('pointerdown', outside, true)
    document.removeEventListener('keydown', esc, true)
    if (focus) button.focus({ preventScroll: true })
  }
  const outside = (e: Event): void => {
    const path = e.composedPath()
    if (path.includes(menu) || path.includes(button)) return   // the button's own click closes it (see above)
    close(false)
  }
  // Esc closes it wherever the focus is (after a tap it may not be in the menu)
  const esc = (e: KeyboardEvent): void => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close() } }
  const draw = (list: MenuItem[], back?: string): void => {
    menu.replaceChildren()
    if (back) {
      const b = el('button', 'menu-i menu-back'); b.type = 'button'; b.setAttribute('role', 'menuitem')
      b.innerHTML = svg('M15 5l-7 7 7 7'); b.append(el('span', 'menu-l', back))
      b.addEventListener('click', () => { draw(items); rows()[0]?.focus({ preventScroll: true }) })
      menu.append(b)
    }
    for (const it of list) {
      const b = el('button', 'menu-i'); b.type = 'button'; b.setAttribute('role', 'menuitem'); b.dataset.id = it.id
      b.innerHTML = it.icon ? svg(it.icon) : back ? '' : '<svg width="20" height="20"></svg>'
      const text = el('span', 'menu-l', it.label)
      if (it.hint) text.append(el('span', 'menu-h', it.hint))
      b.append(text)
      if (it.items) { b.setAttribute('aria-haspopup', 'menu'); const c = el('span', 'menu-c'); c.innerHTML = svg('M9 5l7 7-7 7'); b.append(c) }
      else if (it.keys?.length && fine) { const k = el('span', 'menu-k'); for (const key of it.keys) k.append(el('kbd', '', keyLabel(key, isMac()))); b.append(k) }
      b.addEventListener('click', () => {
        if (it.items) { draw(it.items, it.label); rows()[1]?.focus({ preventScroll: true }); return }
        close(); pick(it)
      })
      menu.append(b)
    }
    place()
  }
  const place = (): void => {
    const b = button.getBoundingClientRect(), h = host.getBoundingClientRect()
    menu.style.left = `${Math.max(8, Math.min(h.width - menu.offsetWidth - 8, b.left - h.left))}px`
    menu.style.bottom = `${h.bottom - b.top + 8}px`
    menu.style.maxHeight = `${Math.max(120, b.top - h.top - 16)}px`
  }
  menu.addEventListener('keydown', (e) => {
    const list = rows(), at = list.indexOf(menu.getRootNode() instanceof ShadowRoot ? (menu.getRootNode() as ShadowRoot).activeElement as HTMLElement : document.activeElement as HTMLElement)
    const go = (i: number): void => { e.preventDefault(); list[(i + list.length) % list.length]?.focus({ preventScroll: true }) }
    if (e.key === 'ArrowDown') go(at + 1)
    else if (e.key === 'ArrowUp') go(at < 0 ? list.length - 1 : at - 1)
    else if (e.key === 'Home') go(0)
    else if (e.key === 'End') go(list.length - 1)
    else if (e.key === 'Tab') close(false)
  })
  adoptTipCss(host)
  host.append(menu)
  const sub = start ? items.find((x) => x.id === start && x.items) : undefined
  if (sub) draw(sub.items!, sub.label); else draw(items)
  button.setAttribute('aria-expanded', 'true'); button.setAttribute('aria-haspopup', 'menu')
  closeOpen = close; openFor = button
  setTimeout(() => document.addEventListener('pointerdown', outside, true), 0)
  document.addEventListener('keydown', esc, true)
  rows()[sub ? 1 : 0]?.focus({ preventScroll: true })
  return close
}

// the one-script build: agui-chat.tip.js registers it on window.AguiChat
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.openMenu = openMenu

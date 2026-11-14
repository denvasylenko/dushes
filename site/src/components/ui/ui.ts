/**
 * The behaviour of the docs design system, wired once for the whole page by event delegation, so markup built later
 * by a component's script works too. Every primitive in this folder imports it; components import the helpers.
 *
 *   [data-ui-choice]        a radiogroup of [role=radio] buttons with data-value (Chips, Segmented, Swatches):
 *                           click or arrow keys select; the group fires a bubbling `ui-change` event, detail {value}
 *   [data-ui-menu]          a trigger [data-ui-menu-trigger] and a .ui-pop: toggles, closes on Esc and outside taps,
 *                           arrow keys move between the items
 *   [data-ui-copy]          a Copy button: copies the selector's text, or the code of the closest .ui-code when empty
 *   input.ui-range          a slider: keeps the accent track (--p) and its <output data-ui-out-for=id> current
 *   [data-ui-masonry]       a gallery: each tile spans as many 1px rows as it is tall, kept current as tiles resize
 */

/** Select `value` in a choice group (no event: the caller already knows). */
export function setChoice(group: Element, value: string): void {
  const all = [...group.querySelectorAll<HTMLElement>('[role="radio"]')]
  const hit = all.some((r) => r.dataset.value === value)
  all.forEach((r, i) => {
    const on = r.dataset.value === value
    r.setAttribute('aria-checked', String(on))
    r.tabIndex = on || (!hit && i === 0) ? 0 : -1   // a value outside the group (a custom colour): Tab still lands on it
  })
}

function pick(radio: HTMLElement, focus = false): void {
  const group = radio.closest<HTMLElement>('[data-ui-choice]')
  if (!group || radio.getAttribute('aria-disabled') === 'true') return
  const value = radio.dataset.value ?? ''
  const changed = radio.getAttribute('aria-checked') !== 'true'
  setChoice(group, value)
  if (focus) radio.focus()
  if (changed) group.dispatchEvent(new CustomEvent('ui-change', { bubbles: true, detail: { value } }))
}

/**
 * Copy text and show it on the button: "Copied" with a check for a moment. `get` may be async (Copy page fetches
 * the Markdown). Returns false when the clipboard refused, so the caller can show the text to copy by hand.
 */
export async function copyText(btn: HTMLElement, get: string | (() => string | Promise<string>)): Promise<boolean> {
  const label = btn.querySelector<HTMLElement>('[data-ui-copy-label]')
  const idle = btn.dataset.idle ?? label?.textContent ?? ''
  btn.dataset.idle = idle
  let ok = true
  try {
    await navigator.clipboard.writeText(typeof get === 'string' ? get : await get())
  } catch { ok = false }
  if (label) label.textContent = ok ? (btn.dataset.done ?? 'Copied') : (btn.dataset.fail ?? 'Select and copy')
  if (ok) btn.dataset.state = 'copied'
  clearTimeout(Number(btn.dataset.timer))
  btn.dataset.timer = String(setTimeout(() => {
    if (label) label.textContent = idle
    delete btn.dataset.state
  }, ok ? 1800 : 2400))
  return ok
}

/** Keep a slider's accent track and output in step with its value. */
export function syncRange(r: HTMLInputElement): void {
  const min = Number(r.min || 0), max = Number(r.max || 100)
  r.style.setProperty('--p', `${((Number(r.value) - min) / (max - min || 1)) * 100}%`)
  const out = r.id ? document.querySelector<HTMLOutputElement>(`[data-ui-out-for="${r.id}"]`) : null
  if (out) out.textContent = `${r.value}${out.dataset.unit ?? ''}`
}

function setMenu(menu: HTMLElement, open: boolean, focus: 'first' | 'trigger' | null = null): void {
  const trigger = menu.querySelector<HTMLElement>('[data-ui-menu-trigger]')
  const pop = menu.querySelector<HTMLElement>('.ui-pop')
  if (!trigger || !pop) return
  pop.hidden = !open
  trigger.setAttribute('aria-expanded', String(open))
  if (open) menu.dispatchEvent(new CustomEvent('ui-open', { bubbles: true }))
  if (focus === 'first') pop.querySelector<HTMLElement>('[role="menuitem"]')?.focus()
  if (focus === 'trigger') trigger.focus()
}

/**
 * Pack a Masonry gallery: every tile spans as many 1px grid rows as it is tall (plus the gap), so a short tile sits
 * right under its neighbour. Watches each tile, so later growth (an image, a font, a disclosure) re-packs. Call it
 * for a gallery built after load; the ones in the page are packed on their own.
 */
export function masonry(grid: HTMLElement): void {
  if (grid.dataset.on !== undefined) return
  const gap = () => parseFloat(getComputedStyle(grid).columnGap) || 0
  const span = (el: HTMLElement) => { el.style.gridRowEnd = `span ${Math.max(1, Math.ceil(el.getBoundingClientRect().height + gap()))}` }
  const ro = new ResizeObserver((entries) => entries.forEach((e) => span(e.target as HTMLElement)))
  const watch = (el: Element) => { if (el instanceof HTMLElement) { span(el); ro.observe(el) } }
  grid.dataset.on = ''
  ;[...grid.children].forEach(watch)
  new MutationObserver((ms) => ms.forEach((m) => m.addedNodes.forEach(watch))).observe(grid, { childList: true })
}

const openMenus = () => [...document.querySelectorAll<HTMLElement>('[data-ui-menu]')].filter((m) => m.querySelector('.ui-pop:not([hidden])'))

if (!(window as { __fgUi?: boolean }).__fgUi) {
  ;(window as { __fgUi?: boolean }).__fgUi = true

  document.addEventListener('click', (e) => {
    const t = e.target as HTMLElement
    const radio = t.closest<HTMLElement>('[data-ui-choice] [role="radio"]')
    if (radio) pick(radio)

    const trigger = t.closest<HTMLElement>('[data-ui-menu-trigger]')
    const inMenu = t.closest<HTMLElement>('[data-ui-menu]')
    for (const m of openMenus()) if (m !== inMenu) setMenu(m, false)
    if (trigger && inMenu) setMenu(inMenu, inMenu.querySelector('.ui-pop')!.hasAttribute('hidden'))
    else if (inMenu && t.closest('[role="menuitem"]')) setMenu(inMenu, false)

    const copy = t.closest<HTMLElement>('[data-ui-copy]')
    if (copy) {
      const sel = copy.dataset.uiCopy
      const src = sel ? document.querySelector(sel) : copy.closest('.ui-code')?.querySelector('code, pre')
      void copyText(copy, src?.textContent ?? '')
    }
  })

  document.addEventListener('keydown', (e) => {
    const t = e.target as HTMLElement
    if (e.key === 'Escape') {
      for (const m of openMenus()) setMenu(m, false, m.contains(t) ? 'trigger' : null)
      return
    }
    const radio = t.closest?.<HTMLElement>('[data-ui-choice] [role="radio"]')
    if (radio && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) {
      const all = [...radio.closest('[data-ui-choice]')!.querySelectorAll<HTMLElement>('[role="radio"]')]
      const i = all.indexOf(radio)
      const n = e.key === 'Home' ? 0 : e.key === 'End' ? all.length - 1
        : (i + (e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 1) + all.length) % all.length
      e.preventDefault()
      pick(all[n], true)
      return
    }
    const menu = t.closest?.<HTMLElement>('[data-ui-menu]')
    if (!menu || !['ArrowDown', 'ArrowUp'].includes(e.key)) return
    if (t.matches('[data-ui-menu-trigger]')) { e.preventDefault(); setMenu(menu, true, 'first'); return }
    const items = [...menu.querySelectorAll<HTMLElement>('[role="menuitem"]')]
    const i = items.indexOf(t)
    if (i < 0) return
    e.preventDefault()
    items[(i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length].focus()
  })

  document.addEventListener('input', (e) => {
    const t = e.target as HTMLElement
    if (t instanceof HTMLInputElement && t.classList.contains('ui-range')) syncRange(t)
  })

  const init = () => {
    document.querySelectorAll<HTMLInputElement>('input.ui-range').forEach(syncRange)
    document.querySelectorAll<HTMLElement>('[data-ui-masonry]').forEach(masonry)
    document.querySelectorAll('[data-ui-choice]').forEach((g) => {
      const on = g.querySelector<HTMLElement>('[role="radio"][aria-checked="true"]') ?? g.querySelector<HTMLElement>('[role="radio"]')
      g.querySelectorAll<HTMLElement>('[role="radio"]').forEach((r) => { r.tabIndex = r === on ? 0 : -1 })
    })
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init()
}

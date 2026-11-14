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
 *   [data-ui-select]        a pop-up menu select (macOS pop-up button; a sheet on a phone): its button opens a listbox
 *                           of options with a check on the chosen one; picking fires a bubbling `ui-change` {value}
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

/* ---------- Select: a pop-up menu with a check (macOS), a sheet on a phone (iOS) ---------- */

export interface SelectOption { value: string; label: string }
export interface SelectInit {
  options: SelectOption[]; value?: string | null; placeholder?: string; id?: string; label?: string
  onChange?: (value: string) => void
}
const SVG = (d: string) => `<svg class="ui-icon" viewBox="0 0 16 16" aria-hidden="true">${d}</svg>`
const UPDOWN = '<path d="M5 6.5 8 3.5l3 3M5 9.5l3 3 3-3"/>'
const CHECK = '<path d="M3.5 8.5 6.5 11.5 12.5 4.5"/>'
let selSeq = 0

/** Build a Select for markup made by script (the demo form). Select.astro renders the same markup on the server. */
export function buildSelect(o: SelectInit): HTMLElement {
  const n = ++selSeq
  const box = document.createElement('div')
  box.className = 'ui-select'
  box.dataset.uiSelect = ''
  const cur = o.options.find((x) => x.value === o.value)
  const listId = `ui-select-l${n}`
  box.innerHTML = `<button type="button" class="ui-select-btn${cur ? '' : ' is-empty'}" aria-haspopup="listbox" aria-expanded="false" aria-controls="${listId}"`
    + `${o.id ? ` id="${o.id}"` : ''}><span class="ui-select-val"></span>${SVG(UPDOWN)}</button>`
    + `<div class="ui-select-pop" id="${listId}" role="listbox" tabindex="-1" hidden><p class="ui-select-title"></p></div>`
  box.querySelector('.ui-select-val')!.textContent = cur?.label ?? o.placeholder ?? 'Choose\u2026'
  const pop = box.querySelector<HTMLElement>('.ui-select-pop')!
  if (o.label) { pop.setAttribute('aria-label', o.label); pop.querySelector('.ui-select-title')!.textContent = o.label }
  for (const x of o.options) {
    const opt = document.createElement('div')
    opt.className = 'ui-select-opt'
    opt.setAttribute('role', 'option')
    opt.tabIndex = -1
    opt.dataset.value = x.value
    opt.setAttribute('aria-selected', String(x.value === o.value))
    opt.innerHTML = SVG(CHECK) + '<span></span>'
    opt.querySelector('span')!.textContent = x.label
    pop.appendChild(opt)
  }
  // the sheet's Cancel, apart from the options (an iOS action sheet); hidden in the desktop menu
  pop.insertAdjacentHTML('beforeend', '<button type="button" class="ui-select-cancel">Cancel</button>')
  if (o.onChange) box.addEventListener('ui-change', (e) => o.onChange!((e as CustomEvent<{ value: string }>).detail.value))
  return box
}

const phoneSheet = () => matchMedia('(max-width: 50rem)').matches
let scrim: HTMLElement | null = null

function setSelect(box: HTMLElement, open: boolean, focus: 'option' | 'button' | null = null): void {
  const btn = box.querySelector<HTMLElement>('.ui-select-btn')
  const pop = box.querySelector<HTMLElement>('.ui-select-pop')
  if (!btn || !pop) return
  pop.hidden = !open
  btn.setAttribute('aria-expanded', String(open))
  box.classList.toggle('is-open', open)
  if (open) {
    const sheet = phoneSheet()
    pop.classList.toggle('is-sheet', sheet)
    if (sheet) {
      scrim ??= Object.assign(document.createElement('div'), { className: 'ui-select-scrim' })
      document.body.appendChild(scrim)
      document.documentElement.classList.add('ui-select-lock')   // the page behind a sheet does not scroll
      pop.style.cssText = ''
    } else {
      // macOS: the menu opens over the button with the chosen option's text on the button's text; with no choice yet it
      // opens under the button. Fixed to the viewport, so a scrolling form panel never clips it; kept inside the window.
      const r = btn.getBoundingClientRect()
      pop.style.position = 'fixed'
      pop.style.minWidth = `${Math.round(r.width)}px`
      pop.style.animation = 'none'
      pop.style.left = '0px'
      pop.style.top = '0px'
      const origin = pop.getBoundingClientRect()   // where "0, 0" really is (an ancestor with a transform moves it)
      const sel = pop.querySelector<HTMLElement>('[role="option"][aria-selected="true"]')
      const val = btn.querySelector<HTMLElement>('.ui-select-val')!.getBoundingClientRect()
      const h = pop.offsetHeight
      let left = r.left, top = r.bottom + 6
      if (sel) {
        const text = sel.querySelector('span')!.getBoundingClientRect(), o = sel.getBoundingClientRect()
        left = r.left - (text.left - origin.left - (val.left - r.left))
        top = r.top - (o.top - origin.top) - (o.height - r.height) / 2
      } else if (innerHeight - r.bottom - 8 < h && r.top >= h) top = r.top - h - 6
      left = Math.max(8, Math.min(left, innerWidth - pop.offsetWidth - 8))
      top = Math.max(8, Math.min(top, innerHeight - h - 8))
      pop.style.left = `${Math.round(left - origin.left)}px`
      pop.style.top = `${Math.round(top - origin.top)}px`
      pop.style.animation = ''
    }
    if (focus === 'option') (pop.querySelector<HTMLElement>('[aria-selected="true"]') ?? pop.querySelector<HTMLElement>('[role="option"]'))?.focus()
  } else {
    scrim?.remove()
    document.documentElement.classList.remove('ui-select-lock')
    if (focus === 'button') btn.focus()
  }
}

function choose(opt: HTMLElement): void {
  const box = opt.closest<HTMLElement>('[data-ui-select]')
  if (!box) return
  const value = opt.dataset.value ?? ''
  const was = box.querySelector('[role="option"][aria-selected="true"]') as HTMLElement | null
  box.querySelectorAll('[role="option"]').forEach((x) => x.setAttribute('aria-selected', String(x === opt)))
  const btn = box.querySelector<HTMLElement>('.ui-select-btn')!
  btn.classList.remove('is-empty')
  btn.querySelector('.ui-select-val')!.textContent = opt.textContent ?? ''
  setSelect(box, false, 'button')
  if (was !== opt) box.dispatchEvent(new CustomEvent('ui-change', { bubbles: true, detail: { value } }))
}

const openSelects = () => [...document.querySelectorAll<HTMLElement>('[data-ui-select].is-open')]

if (!(window as { __fgSel?: boolean }).__fgSel) {
  ;(window as { __fgSel?: boolean }).__fgSel = true
  document.addEventListener('click', (e) => {
    const t = e.target as HTMLElement
    const box = t.closest<HTMLElement>('[data-ui-select]')
    for (const b of openSelects()) if (b !== box) setSelect(b, false)
    if (!box) return
    if (t.closest('.ui-select-cancel')) return setSelect(box, false, 'button')
    const opt = t.closest<HTMLElement>('[role="option"]')
    if (opt) return choose(opt)
    if (t.closest('.ui-select-btn')) setSelect(box, !box.classList.contains('is-open'), 'option')
  })
  document.addEventListener('keydown', (e) => {
    const t = e.target as HTMLElement
    const box = t.closest?.<HTMLElement>('[data-ui-select]')
    if (!box) return
    const open = box.classList.contains('is-open')
    if (t.matches('.ui-select-btn')) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key) && !open) { e.preventDefault(); setSelect(box, true, 'option') }
      return
    }
    const opts = [...box.querySelectorAll<HTMLElement>('[role="option"]')]
    const i = opts.indexOf(t)
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); setSelect(box, false, 'button') }
    else if (e.key === 'Tab') setSelect(box, false)
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); opts[Math.max(0, Math.min(opts.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))]?.focus() }
    else if (e.key === 'Home' || e.key === 'End') { e.preventDefault(); opts[e.key === 'Home' ? 0 : opts.length - 1]?.focus() }
    else if ((e.key === 'Enter' || e.key === ' ') && i >= 0) { e.preventDefault(); choose(opts[i]) }
  })
  // a pop-up menu does not ride along with the page: scrolling or resizing closes it (a sheet stays)
  const closeFloating = () => openSelects().forEach((b) => { if (!b.querySelector('.is-sheet')) setSelect(b, false) })
  addEventListener('scroll', (e) => { if (!(e.target as Element)?.closest?.('.ui-select-pop')) closeFloating() }, true)
  addEventListener('resize', closeFloating)
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

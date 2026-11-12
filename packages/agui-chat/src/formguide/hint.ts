/**
 * "Look here" on a page the widget does not own: scroll to the field, focus it, ring it for 2.5 s and,
 * when the agent sent a hint, show it in a small bubble under the field for a few seconds.
 * System colours (Canvas, CanvasText, Highlight) keep it readable on any page, light or dark.
 */
const HINT_MS = 6000
let current: { el: HTMLElement; timer: number } | null = null

function clearHint(): void {
  if (!current) return
  clearTimeout(current.timer)
  current.el.remove()
  current = null
}

/** A bubble under `field` with `text`; one at a time, gone after a few seconds or on click. */
export function showHint(field: HTMLElement, text: string): void {
  clearHint()
  if (!text.trim()) return
  const r = field.getBoundingClientRect()
  const el = document.createElement('div')
  el.setAttribute('role', 'status')
  el.dataset.formguideHint = ''
  el.textContent = text
  Object.assign(el.style, {
    position: 'absolute', zIndex: '2147482998', maxWidth: `${Math.min(360, window.innerWidth - 32)}px`,
    left: `${Math.max(16, Math.min(r.left + window.scrollX, window.scrollX + window.innerWidth - 376))}px`,
    top: `${r.bottom + window.scrollY + 8}px`,
    background: 'Canvas', color: 'CanvasText', border: '2px solid Highlight', borderRadius: '10px',
    padding: '8px 12px', font: '500 13px/1.4 system-ui, -apple-system, sans-serif',
    boxShadow: '0 6px 24px -8px rgba(0,0,0,.35)', cursor: 'pointer',
  } satisfies Partial<CSSStyleDeclaration>)
  el.addEventListener('click', clearHint)
  document.body.appendChild(el)
  current = { el, timer: window.setTimeout(clearHint, HINT_MS) }
}

/** Find a field by data-name (or an input's name), scroll to it, focus it, ring it, show the hint. */
export function lookAt(name: string, hint = ''): boolean {
  const sel = `[data-name="${CSS.escape(name)}"], [name="${CSS.escape(name)}"]`
  const el = document.querySelector<HTMLElement>(sel)
  if (!el) return false
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  const touch = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches
  const input = el.matches('input, select, textarea') ? el : el.querySelector<HTMLElement>('input, select, textarea')
  if (input && !touch) input.focus({ preventScroll: true })   // a phone would open its keyboard
  const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
  const ring = { outline: '3px solid Highlight', outlineOffset: '4px' }
  const frames = reduce ? [ring, ring] : [{ ...ring, outlineColor: 'transparent' }, ring, ring, ring, { ...ring, outlineColor: 'transparent' }]
  el.animate?.(frames, { duration: 2500, easing: 'ease-out' })   // reduced motion: the ring just stays, no fade
  // the bubble goes where the field ends up after the smooth scroll
  window.setTimeout(() => showHint(el, hint), reduce ? 0 : 350)
  return true
}

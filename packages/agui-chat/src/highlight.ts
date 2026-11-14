/**
 * The field highlight, public and on its own: the ring and the green blink a field gets when the agent changes it,
 * and the ring, the scroll and the hint of "look here". Any page can put it on its own fields, with or without the
 * chat:
 *
 *   import { highlightField } from '@formguide/agui-chat/highlight'
 *   highlightField('amount')                                    // [data-name="amount"], else [name="amount"]
 *   highlightField('email', { kind: 'look', hint: 'As on your ID' })
 *
 * It marks the field with data-agui-highlight="changed|look" and data-agui-highlight-style="ring|glow|pulse" for
 * the length of the effect and draws from CSS variables, shared tokens first (herefront-ui --hf-*), then the
 * widget's own, then today's look:
 *   colour   changed: --hf-ok, else --agui-highlight-color, else green; look: --hf-accent, else the same, else Highlight
 *   width    --hf-hl-w, else --agui-highlight-width (3px)       strength  --hf-hl-mix, else --agui-highlight-mix (45%)
 *   fade-in  --hf-hl-dur, else .3s                              easing    --hf-motion-ease, else --agui-ease
 *   length   --agui-highlight-ms (1200, in ms)                  blinks    --agui-highlight-count (2)
 *   corners  --agui-highlight-radius (else the field's own)
 * Reduced motion: a steady ring for the same time, no blink. The stylesheet comes with it (the document, or the
 * shadow root that holds the field), so a page needs no CSS. Also <agui-highlight name="amount">: a box to wrap a
 * field in.
 */

export interface HighlightOptions {
  /** 'changed' (default): the agent set a value, mark it; 'look': also scroll to it, focus it, show `hint`. */
  kind?: 'changed' | 'look'
  hint?: string
  style?: 'ring' | 'glow' | 'pulse'
  /** Where to look for a field named by a string (default: the document). */
  root?: ParentNode
  /** Scroll to the field (default: only for 'look'). */
  scroll?: boolean
  /** Where `hint` shows: 'inside' (default: a small pill in the field's top-right corner, as on the landing) or
   *  'below' (a bubble under it, also used when the field is too small to hold the pill). */
  hintAt?: 'inside' | 'below'
}

export const HIGHLIGHT_CSS = `
[data-agui-highlight] {
  --agui-hl-c: var(--hf-ok, var(--agui-highlight-color, #34c759));
  --agui-hl-ring: color-mix(in srgb, var(--agui-hl-c) var(--hf-hl-mix, var(--agui-highlight-mix, 45%)), transparent);
  outline: var(--hf-hl-w, var(--agui-highlight-width, 3px)) solid var(--agui-hl-ring); outline-offset: 3px;
  /* fades in (no outline-color transition: it would start from the text colour, a dark frame) */
  transition: box-shadow var(--hf-hl-dur, .3s) var(--hf-motion-ease, var(--agui-ease, ease));
  animation: agui-hl-blink var(--agui-hl-cycle, 600ms) var(--hf-motion-ease, var(--agui-ease, ease)) var(--agui-hl-n, 2);
}
[data-agui-highlight=look] { --agui-hl-c: var(--hf-accent, var(--agui-highlight-color, #0071e3)); animation-name: agui-hl-soft; }
[data-agui-highlight-style=glow] { outline-color: transparent; box-shadow: 0 0 0 var(--hf-hl-w, var(--agui-highlight-width, 3px)) var(--agui-hl-ring), 0 0 18px 2px var(--agui-hl-ring); animation-name: agui-hl-glow; }
[data-agui-highlight-style=pulse] { animation-name: agui-hl-pulse; }
@keyframes agui-hl-blink { 0%, 100% { outline-color: var(--agui-hl-ring); } 50% { outline-color: transparent; } }
@keyframes agui-hl-glow { 0%, 100% { box-shadow: 0 0 0 var(--hf-hl-w, var(--agui-highlight-width, 3px)) var(--agui-hl-ring), 0 0 18px 2px var(--agui-hl-ring); } 50% { box-shadow: 0 0 0 0 transparent; } }
@keyframes agui-hl-soft { 0% { box-shadow: 0 0 0 0 var(--agui-hl-ring); opacity: 1; } 100% { box-shadow: 0 0 0 10px transparent; } }
@keyframes agui-hl-pulse { 0%, 100% { outline-offset: 3px; } 50% { outline-offset: 7px; } }
[data-agui-highlight][data-agui-highlight-out] { animation: agui-hl-out var(--hf-hl-dur, .3s) var(--hf-motion-ease, var(--agui-ease, ease)) forwards; }
@keyframes agui-hl-out { from { outline-color: var(--agui-hl-ring); } to { outline-color: transparent; box-shadow: 0 0 0 0 transparent; } }
@media (prefers-reduced-motion: reduce) { [data-agui-highlight] { animation: none; transition: none; } }
agui-highlight { display: block; }
/* the hint: a small pill in the field's top-right corner, the field's own; it comes and goes with the ring */
.agui-hl-hint { position: absolute; z-index: 3; top: 6px; right: 8px; max-width: 70%; padding: 2px 8px; border-radius: 999px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; pointer-events: auto; cursor: pointer;
  font: 500 11px/16px var(--hf-font-sans, system-ui, -apple-system, sans-serif);
  color: var(--hf-accent, var(--agui-highlight-color, #0071e3)); background: color-mix(in srgb, var(--hf-accent, var(--agui-highlight-color, #0071e3)) 12%, Canvas);
  transition: opacity var(--hf-hl-dur, .3s) var(--hf-motion-ease, var(--agui-ease, ease)); }
.agui-hl-hint.out { opacity: 0; }
.agui-hl-hint.below { position: absolute; top: auto; right: auto; max-width: min(360px, calc(100vw - 32px)); white-space: normal; padding: 6px 10px;
  border-radius: 10px; font-size: 13px; line-height: 1.4; z-index: 2147482998; }
@media (prefers-reduced-motion: reduce) { .agui-hl-hint { transition: none; } }
`

const styled = new WeakSet<Node>()
/** The stylesheet, once per root: the document, or the shadow root that holds the field. */
function style(node: Node): void {
  const root = node.getRootNode() as Document | ShadowRoot
  if (styled.has(root)) return
  styled.add(root)
  try {
    const sh = new CSSStyleSheet(); sh.replaceSync(HIGHLIGHT_CSS)
    root.adoptedStyleSheets = [...root.adoptedStyleSheets, sh]
  } catch {
    const el = document.createElement('style'); el.textContent = HIGHLIGHT_CSS
    ;(root instanceof Document ? root.head : root).append(el)
  }
}

const reduced = (): boolean => !!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const touch = (): boolean => !!globalThis.matchMedia?.('(pointer: coarse)').matches

/** A field by name: [data-name], then [name]; an input inside a [data-name] box rings the box. */
function find(target: string | HTMLElement, root: ParentNode = document): HTMLElement | null {
  let el = typeof target === 'string'
    ? root.querySelector<HTMLElement>(`[data-name="${CSS.escape(target)}"]`) ?? root.querySelector<HTMLElement>(`[name="${CSS.escape(target)}"]`)
    : target
  if (el && el.matches('input, select, textarea')) el = el.closest<HTMLElement>('[data-name]') ?? el
  return el
}

const running = new WeakMap<HTMLElement, () => void>()
let bubble: { el: HTMLElement; undo: () => void } | null = null

/** The hint goes: faded out with the ring (the same length and curve), at once with reduced motion. */
function clearHint(now = false): void {
  if (!bubble) return
  const { el, undo } = bubble
  bubble = null
  const gone = (): void => { el.remove(); undo() }
  if (now || reduced()) return gone()
  el.classList.add('out')
  setTimeout(gone, fadeMs(el))
}

/** --hf-hl-dur (the shared fade) in ms; .3 s without it. */
function fadeMs(el: HTMLElement): number {
  const v = getComputedStyle(el).getPropertyValue('--hf-hl-dur').trim()
  const n = parseFloat(v)
  return !n ? 300 : /ms$/.test(v) ? n : n * 1000
}

/** The agent's hint: a pill inside the field's top-right corner (the field's own, so the eye stays there), or a
 *  bubble under it when the field is too small or `at` says so. It lives with the ring: shown with it, gone with it
 *  (or, when the user is in the field, once the focus leaves). */
function showHint(field: HTMLElement, text: string, at: 'inside' | 'below' = 'inside'): void {
  clearHint(true)
  if (!text.trim()) return
  const r = field.getBoundingClientRect()
  const inside = at === 'inside' && !field.matches('input, select, textarea, img') && r.width >= 160 && r.height >= 40
  const el = document.createElement('div')
  el.className = inside ? 'agui-hl-hint' : 'agui-hl-hint below'
  el.dataset.formguideHint = ''   // the name hosts styled it by before
  el.setAttribute('role', 'status')
  el.textContent = text
  el.title = text
  let undo = (): void => {}
  if (inside) {
    if (['static', ''].includes(getComputedStyle(field).position)) {   // the pill sits in the field's corner: the field holds it
      const was = field.style.position
      field.style.position = 'relative'
      undo = () => { field.style.position = was }
    }
    style(field)
    field.append(el)
  } else {
    el.style.left = `${Math.max(16, Math.min(r.left + scrollX, scrollX + innerWidth - 376))}px`
    el.style.top = `${r.bottom + scrollY + 8}px`
    style(document)
    document.body.append(el)
  }
  el.addEventListener('click', () => clearHint(true))
  bubble = { el, undo }
}

/** Highlight a field: returns a function that ends it early. Calling it again on the same field restarts it. */
export function highlightField(target: string | HTMLElement, opts: HighlightOptions = {}): () => void {
  const el = find(target, opts.root)
  if (!el) return () => {}
  running.get(el)?.()   // again on the same field: start over
  clearHint(true)   // a new highlight takes the last hint away
  style(el)
  const kind = opts.kind ?? 'changed'
  const cs = getComputedStyle(el)
  const ms = Number(cs.getPropertyValue('--agui-highlight-ms').trim()) || (kind === 'look' ? 4000 : 1200)   // look: time to read the hint
  const count = Math.max(1, Math.round(Number(cs.getPropertyValue('--agui-highlight-count').trim()) || 2))
  const radius = cs.getPropertyValue('--agui-highlight-radius').trim()
  const oldRadius = el.style.borderRadius
  el.style.setProperty('--agui-hl-cycle', `${Math.round(ms / count)}ms`)
  el.style.setProperty('--agui-hl-n', String(count))
  if (radius) el.style.borderRadius = radius
  el.dataset.aguiHighlight = kind
  el.dataset.aguiHighlightStyle = opts.style ?? 'ring'
  if (opts.scroll ?? kind === 'look') el.scrollIntoView?.({ behavior: reduced() ? 'auto' : 'smooth', block: 'center' })
  if (kind === 'look') {
    const input = el.matches('input, select, textarea') ? el : el.querySelector<HTMLElement>('input, select, textarea')
    if (input && !touch()) input.focus({ preventScroll: true })   // a phone would open its keyboard
    if (opts.hint) setTimeout(() => showHint(el, opts.hint!, opts.hintAt), reduced() ? 0 : 350)   // once the scroll has settled
  }
  let fading: ReturnType<typeof setTimeout> | undefined
  const clean = (): void => {
    clearTimeout(fading)
    delete el.dataset.aguiHighlight
    delete el.dataset.aguiHighlightStyle
    delete el.dataset.aguiHighlightOut
    el.style.removeProperty('--agui-hl-cycle'); el.style.removeProperty('--agui-hl-n')
    if (radius) el.style.borderRadius = oldRadius
  }
  /** The natural end fades the ring and the hint out together; cancel() and a restart end at once. */
  const end = (fade = false): void => {
    clearTimeout(timer)
    if (running.get(el) !== stop) return
    running.delete(el)
    const mine = bubble && el.contains(bubble.el) ? bubble : null
    // the user is in the field: the hint stays until the focus leaves; the ring goes now
    if (mine && el.contains(document.activeElement)) el.addEventListener('focusout', () => { if (bubble === mine) clearHint() }, { once: true })
    else if (mine || (kind === 'look' && bubble)) clearHint(!fade)
    if (!fade || reduced()) return clean()
    el.dataset.aguiHighlightOut = ''   // the ring fades out (same length and curve as the hint)
    fading = setTimeout(clean, fadeMs(el))
  }
  const stop = (): void => end(false)
  const timer = setTimeout(() => end(true), ms)
  running.set(el, stop)
  return stop
}

/** "Look here" (the plugin's default directive): scroll, focus, ring, the hint; true when the field was found. */
export function lookAt(name: string, hint = ''): boolean {
  if (!find(name)) return false
  highlightField(name, { kind: 'look', hint })
  return true
}

/** <agui-highlight name="amount">: a block box carrying data-name, for a field of your own. */
export class AguiHighlightElement extends HTMLElement {
  static observedAttributes = ['name']
  connectedCallback(): void { style(this); this.attributeChangedCallback() }
  attributeChangedCallback(): void { const n = this.getAttribute('name'); if (n) this.dataset.name = n; else delete this.dataset.name }
}
if (typeof customElements !== 'undefined' && !customElements.get('agui-highlight')) customElements.define('agui-highlight', AguiHighlightElement)

// the one-script build: agui-chat.highlight.js registers it on window.AguiChat
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) Object.assign(g.AguiChat, { highlightField, lookAt })

/**
 * Where an answer came from: a row of source links under it, and what a tap opens. On a phone a sheet rises from the
 * bottom of the chat (as a sheet on iOS: a grabber, the title, a round close button; a swipe down, the veil or Esc
 * closes it); with a mouse a popover opens over the link (Esc, a click outside or the conversation moving closes it).
 * Both show the document and its section, the passage with the lines the answer rests on marked, "1 of N" to page
 * through the sources (the arrow keys too), and "Open document" when the host gave a link. Nothing in the
 * conversation moves.
 *
 * Loaded with the tooltip (agui-chat.tip.js) when the first sources arrive; its styles are in tip-css.ts.
 * Self-contained (no chat state): fillSources(box, items, t).
 */
import { attachTip } from './tip'
import { adoptTipCss } from './tip-css'

export interface Source {
  title: string; section?: string; quote?: string
  id?: string; doc_id?: string; path?: string | string[]; page?: number | string
  /** The section's text, plain. */
  excerpt?: string
  /** Character ranges [[start, end]] in `excerpt`: the lines the answer rests on. */
  marks?: [number, number][]
  /** The host's own copy of the document. */
  url?: string
}
type T = (key: string, vars?: Record<string, string | number>) => string

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, text?: string): HTMLElementTagNameMap[K] => {
  const e = document.createElement(tag); if (cls) e.className = cls
  if (text !== undefined) e.textContent = text
  return e
}
const icon = (d: string, size = 16): string => `<svg viewBox="0 0 20 20" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`
const DOC = 'M5.5 2.5h6l3.5 3.5v11.5h-9.5zM11.5 2.5V6H15', X = 'M5.5 5.5l9 9m0-9-9 9', PREV = 'M12.5 4.5 7 10l5.5 5.5', NEXT = 'M7.5 4.5 13 10l-5.5 5.5'

const where = (s: Source, t: T): string => [Array.isArray(s.path) ? s.path.join(' › ') : s.path || s.section, s.page ? t('pageN', { n: s.page }) : '']
  .filter(Boolean).join(' · ')
/** The host's link as sent (never rebuilt: a text fragment after # must survive): http(s), or a path on the same site. */
const link = (s: Source): string => (s.url && /^(https?:\/\/|\/(?!\/))/i.test(s.url) ? s.url : '')
/** What a tap can show: a passage (or the short quote) or the host's link. A source with neither stays a plain label. */
const opens = (s: Source): boolean => !!(s.excerpt || s.quote || link(s))
const still = (): boolean => !globalThis.matchMedia || globalThis.matchMedia('(prefers-reduced-motion: reduce)').matches

/** The passage as text nodes, the marked ranges in <mark>. Ranges out of order or out of the text are skipped. */
function passage(s: Source): HTMLElement {
  const box = el('div', 'src-text')
  const text = s.excerpt ?? ''
  if (!text) { if (s.quote) box.append(el('mark', '', s.quote)); return box }
  let at = 0
  for (const [a, b] of [...(s.marks ?? [])].sort((x, y) => x[0] - y[0])) {
    if (!(a >= at && b > a && b <= text.length)) continue
    if (a > at) box.append(text.slice(at, a))
    box.append(el('mark', '', text.slice(a, b)))
    at = b
  }
  if (at < text.length) box.append(text.slice(at))
  return box
}

let closeOpen: (() => void) | null = null

/** Draw the source links into `box` (already in the conversation, so nothing below it moves when they arrive). */
export function fillSources(box: HTMLElement, items: Source[], t: T): void {
  const host = box.closest<HTMLElement>('.panel') ?? box.parentElement!
  adoptTipCss(host)
  const can = items.filter(opens)
  const chips = new Map<Source, HTMLElement>()
  box.replaceChildren(...items.map((s) => {
    const label = `${s.title}${s.section ? ` › ${s.section}` : ''}`
    const chip = el(opens(s) ? 'button' : 'span', 'src')
    chip.setAttribute('part', 'source')
    if (chip instanceof HTMLButtonElement) {   // only a link that opens something looks like one: the fill and the glyph
      chip.innerHTML = icon(DOC, 14)
      chip.type = 'button'
      chip.setAttribute('aria-haspopup', 'dialog')
      chip.setAttribute('aria-expanded', 'false')
      chip.addEventListener('click', () => open(s))
      attachTip(chip, host, () => (chip.getAttribute('aria-expanded') === 'true' ? [] : [{ label: t('showSource') }]))
    }
    chip.append(el('b', '', label))
    chips.set(s, chip)
    return chip
  }))

  function open(first: Source): void {
    const again = chips.get(first)?.getAttribute('aria-expanded') === 'true'
    closeOpen?.()
    if (again) return   // the link toggles
    const sheet = !!globalThis.matchMedia?.('(hover: none)').matches || host.clientWidth < 480
    const veil = sheet ? el('div', 'src-veil') : null
    const view = el('div', sheet ? 'src-view src-sheet' : 'src-view src-pop')
    view.setAttribute('role', 'dialog')
    view.setAttribute('part', 'source-view')
    view.tabIndex = -1
    if (sheet) view.setAttribute('aria-modal', 'true')
    const body = el('div', 'src-body')
    const live = el('span', 'src-live'); live.setAttribute('aria-live', 'polite')   // one region for the whole visit: "2 of 3, Access Control Standard"
    view.append(body, live)
    const log = box.closest<HTMLElement>('.log')
    let now = first

    const turn = (d: number): void => {
      const next = can[can.indexOf(now) + d]
      if (!next) return
      now = next
      draw()
      ;(view.querySelector<HTMLElement>(`.src-go:not(:disabled)[data-d="${d}"]`) ?? view.querySelector<HTMLElement>('.src-go:not(:disabled)') ?? view).focus({ preventScroll: true })
    }
    const draw = (): void => {
      for (const [s, c] of chips) { c.classList.toggle('on', s === now); if (c instanceof HTMLButtonElement) c.setAttribute('aria-expanded', String(s === now)) }
      // the link in view inside its own row (never the conversation)
      const cr = chips.get(now)!.getBoundingClientRect(), br = box.getBoundingClientRect()
      if (cr.left < br.left) box.scrollLeft -= br.left - cr.left + 8
      else if (cr.right > br.right - 28) box.scrollLeft += cr.right - br.right + 36
      const head = el('div', 'src-head')
      const names = el('div', '')
      const title = el('b', '', now.title); title.title = now.title
      names.append(title)
      const sub = where(now, t)
      if (sub) { const small = el('small', '', sub); small.title = sub; names.append(small) }
      const x = el('button', 'src-x'); x.type = 'button'; x.innerHTML = icon(X, 14); x.setAttribute('aria-label', t('close')); x.addEventListener('click', shut)
      head.append(names, x)
      view.setAttribute('aria-label', now.title)
      const text = passage(now)
      const foot = el('div', 'src-foot')
      const i = can.indexOf(now)
      if (can.length > 1) {
        const pager = el('div', 'src-pager')
        const go = (d: number, path: string, key: string): HTMLButtonElement => {
          const b = el('button', 'src-go'); b.type = 'button'; b.innerHTML = icon(path); b.setAttribute('aria-label', t(key)); b.dataset.d = String(d)
          b.disabled = !can[i + d]
          b.addEventListener('click', () => turn(d))
          return b
        }
        pager.append(go(-1, PREV, 'prevSource'), el('span', '', t('ofN', { i: i + 1, n: can.length })), go(1, NEXT, 'nextSource'))
        foot.append(pager)
      }
      if (link(now)) {
        const a = el('a', sheet ? 'btn pri' : 'btn link', t('openDoc'))
        a.setAttribute('href', link(now)); a.target = '_blank'; a.rel = 'noopener noreferrer'
        foot.append(a)
      }
      body.replaceChildren(...(sheet ? [el('span', 'src-grab')] : []), head, ...(text.childNodes.length ? [text] : []), ...(foot.childNodes.length ? [foot] : []))
      const m = text.querySelector('mark')   // the used lines first, inside the passage's own scroll (never the conversation's)
      if (m) text.scrollTop = m.getBoundingClientRect().top - text.getBoundingClientRect().top - text.clientHeight / 3
      live.textContent = can.length > 1 ? `${t('ofN', { i: i + 1, n: can.length })}, ${now.title}${sub ? `, ${sub}` : ''}` : ''
      box.dispatchEvent(new CustomEvent('agui:source-open', { bubbles: true, composed: true, detail: { source: now } }))
    }
    /** The popover over the link it opened from (under it when there is no room above), kept inside the chat. It
     *  stays there while the sources are paged, so "next" does not slide from under the pointer. */
    const place = (): void => {
      const c = chips.get(first)!.getBoundingClientRect(), h = host.getBoundingClientRect()
      const w = view.offsetWidth, ht = view.offsetHeight
      let top = c.top - h.top - ht - 8
      if (top < 8) top = Math.min(c.bottom - h.top + 8, h.height - ht - 8)
      view.style.left = `${Math.max(8, Math.min(h.width - w - 8, c.left - h.left))}px`
      view.style.top = `${Math.max(8, top)}px`
    }
    function shut(): void {
      if (closeOpen !== shut) return
      closeOpen = null
      document.removeEventListener('keydown', onKey, true)
      document.removeEventListener('pointerdown', onDown, true)
      log?.removeEventListener('scroll', shut)
      globalThis.removeEventListener?.('resize', shut)
      const root = view.getRootNode() as ShadowRoot | Document
      const inside = !root.activeElement || view.contains(root.activeElement)
      const gone = (): void => { veil?.remove(); view.remove() }
      if (still()) gone(); else { view.classList.add('out'); veil?.classList.add('out'); setTimeout(gone, 160) }   // it leaves the way it came
      const chip = chips.get(now)
      for (const c of chips.values()) { c.classList.remove('on'); if (c instanceof HTMLButtonElement) c.setAttribute('aria-expanded', 'false') }
      if (chip?.isConnected && inside) chip.focus({ preventScroll: true })
    }
    function onKey(e: KeyboardEvent): void {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); shut(); return }
      const root = view.getRootNode() as ShadowRoot | Document
      const cur = root.activeElement
      if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && cur && view.contains(cur)) { e.preventDefault(); turn(e.key === 'ArrowLeft' ? -1 : 1); return }
      if (e.key !== 'Tab' || !sheet) return
      // a sheet holds the focus while it is open
      const f = [...view.querySelectorAll<HTMLElement>('button:not(:disabled), a[href]')]
      const last = f[f.length - 1]
      if (e.shiftKey ? cur === f[0] || cur === view : cur === last) { e.preventDefault(); (e.shiftKey ? last : f[0]).focus() }
    }
    function onDown(e: PointerEvent): void {
      const path = e.composedPath()
      if (path.includes(view) || [...chips.values()].some((c) => path.includes(c))) return
      shut()
    }
    if (veil) {
      // a swipe down from the top of the sheet (the grabber, the title) closes it, as on iOS; a short one springs back
      let y0: number | null = null
      view.addEventListener('pointerdown', (e) => {
        const at = e.target as HTMLElement
        if (!at.closest('.src-grab, .src-head') || at.closest('button')) return
        y0 = e.clientY; view.classList.add('drag')
        try { view.setPointerCapture(e.pointerId) } catch { /* a synthetic pointer */ }
      })
      view.addEventListener('pointermove', (e) => { if (y0 !== null) view.style.transform = `translateY(${Math.max(0, e.clientY - y0)}px)` })
      const up = (e: PointerEvent): void => {
        if (y0 === null) return
        const d = e.clientY - y0; y0 = null
        view.classList.remove('drag')
        if (d > 60) shut(); else view.style.transform = ''
      }
      view.addEventListener('pointerup', up); view.addEventListener('pointercancel', up)
      host.append(veil)
    } else {
      // a popover belongs to its link: when the conversation moves or the window changes, it goes
      log?.addEventListener('scroll', shut, { passive: true })
      globalThis.addEventListener?.('resize', shut)
      view.addEventListener('focusout', (e) => { const to = e.relatedTarget as Node | null; if (to && !view.contains(to) && ![...chips.values()].includes(to as HTMLElement)) shut() })
    }
    host.append(view)
    closeOpen = shut
    document.addEventListener('keydown', onKey, true)
    document.addEventListener('pointerdown', onDown, true)
    draw()
    if (!sheet) place()
    view.focus({ preventScroll: true })
  }
}

// the one-script build: agui-chat.tip.js registers it on window.AguiChat
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.fillSources = fillSources

/**
 * The image view, like Photos and the Claude app: the picture over the chat, a bar on top with x, the file's name and
 * "1 of 2", and a pencil; the images of one message (or of the composer) page with a swipe, the arrows beside the
 * picture and the arrow keys. An image still in the composer has the pencil: markup (editor.ts), whose check mark
 * puts the marked-up copy in its place; a sent picture is only viewed. Loaded the first time an
 * image is opened (agui-chat.editor.js next to the one-script build), with its own styles, so the chat stays small.
 */
import { h } from './dom'
import { openEditor, type Shape } from './editor'

export interface ZoomHost {
  wrap: HTMLElement
  t: (key: string, vars?: Record<string, string | number>) => string
  icon: (el: HTMLElement, name: 'close') => void
  /** Puts a marked-up copy in place of a composer image (the opener with data-file); absent when uploads are off. */
  mark?: (opener: HTMLElement, image: Blob, name: string) => void
}

const CSS = `
.zoom { position: fixed; inset: 0; width: 100%; height: 100%; max-width: none; max-height: none; margin: 0; padding: 0; border: 0; box-sizing: border-box;
  display: grid; grid-template-rows: auto minmax(0, 1fr); color: white; animation: zoom-in .2s var(--agui-ease) both;
  background: black; }   /* black in both schemes, like Photos: nothing of the chat shows through */
.zoom::backdrop { background: transparent; }
.zoom:not([open]) { display: none; }
.zoom-top { display: grid; grid-template-columns: 44px minmax(0, 1fr) 44px; align-items: center; gap: 12px;
  padding: max(10px, env(safe-area-inset-top, 0px)) 12px 10px; }
.zoom-title { text-align: center; min-width: 0; line-height: 1.25; }
.zoom-name { display: block; font: 600 15px/20px var(--agui-font, inherit); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.zoom-n { display: block; font-size: 13px; color: color-mix(in srgb, white 64%, transparent); font-variant-numeric: tabular-nums; }
.zoom-x, .mk-round { width: 44px; height: 44px; border: 0; border-radius: 50%; display: grid; place-items: center; cursor: pointer; padding: 0;
  background: color-mix(in srgb, white 14%, transparent); color: white; -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
.zoom-x:hover, .mk-round:hover:not(:disabled) { background: color-mix(in srgb, white 22%, transparent); }
.zoom-x svg { width: 20px; height: 20px; }
.zoom-x:focus-visible, .mk-round:focus-visible, .zoom-go:focus-visible, .mk-pal button:focus-visible { outline: 2px solid var(--agui-accent); outline-offset: 2px; }
.zoom-stage { position: relative; min-height: 0; touch-action: pan-y; cursor: zoom-out; --side: 16px; }
/* centred in what is left under the bar, never bigger than it: absolute, so a tall photo cannot stretch the row */
.zoom-stage img { position: absolute; inset: 0 var(--side) 24px; margin: auto; max-width: calc(100% - 2 * var(--side)); max-height: calc(100% - 24px);
  width: auto; height: auto; object-fit: contain; border-radius: var(--agui-radius-sm); cursor: default; }
.zoom-go { position: absolute; top: calc(50% - 34px); width: 44px; height: 44px; border: 0; border-radius: 50%; display: grid; place-items: center; cursor: pointer;
  background: color-mix(in srgb, white 14%, transparent); color: white; }
.zoom-go.prev { left: 16px; } .zoom-go.next { right: 16px; }
.zoom-go:disabled { opacity: .3; cursor: default; }
@media (hover: none) { .zoom-go { display: none; } }   /* a phone swipes */
@media (min-width: 700px) and (hover: hover) { .zoom-stage { --side: 76px; } }   /* room for the arrows beside the picture */
.zoom.marking .zoom-top, .zoom.marking .zoom-stage { visibility: hidden; }
@keyframes zoom-in { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .zoom { animation: none; } }
`

/** A picture we may draw on and read back: ours (blob:, data:) or from this site; another site's would taint the canvas. */
const markable = (src: string): boolean => {
  try { return /^(blob|data):/.test(src) || new URL(src, location.href).origin === location.origin } catch { return false }
}

const PENCIL = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20l4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20zM14 7l3 3"/></svg>'

export function openZoom(host: ZoomHost, opener: HTMLElement, legacyEdit?: (image: Blob) => void): void {
  // the images of one message page together; so do the ones in the composer
  const own = opener.closest('.att-row, .files')
  const openers = own ? [...own.querySelectorAll<HTMLElement>('.att-open')] : [opener]
  const pic = (b: HTMLElement): HTMLImageElement | null => (b instanceof HTMLImageElement ? b : b.querySelector('img'))   // a picture in an answer opens itself
  const row = openers.map((b) => ({ el: b, src: pic(b)?.getAttribute('src') ?? '', name: b.getAttribute('aria-label') || pic(b)?.alt || '' }))
  let at = Math.max(0, openers.indexOf(opener))
  const drawn = new Map<number, Shape[]>()   // what was drawn on each image while the view is open: x in markup keeps it

  const x = h('button', { class: 'zoom-x', type: 'button', 'aria-label': host.t('close') }); host.icon(x, 'close')
  const name = h('span', { class: 'zoom-name' })
  const count = h('span', { class: 'zoom-n', 'aria-live': 'polite' })
  const pencil = h('button', { class: 'zoom-x zoom-edit', type: 'button', 'aria-label': host.t('markup') })
  pencil.innerHTML = PENCIL
  const img = h('img', { alt: '' }) as HTMLImageElement
  const stage = h('div', { class: 'zoom-stage' }, img)
  const view = h('dialog', { class: 'zoom', part: 'zoom' },
    h('style', {}, CSS), h('div', { class: 'zoom-top' }, x, h('span', { class: 'zoom-title' }, name, count), pencil), stage) as HTMLDialogElement

  // only an image not sent yet: what was sent stays as it was (Messages works the same way)
  const canMark = (i: number): boolean => !!row[i]?.src && markable(row[i].src) && row[i].el.dataset.file !== undefined && (!!host.mark || (!!legacyEdit && row[i].el === opener))
  const go = (d: number): HTMLButtonElement => {
    const b = h('button', { class: `zoom-go ${d < 0 ? 'prev' : 'next'}`, type: 'button', 'aria-label': host.t(d < 0 ? 'prevImage' : 'nextImage') }) as HTMLButtonElement
    b.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d < 0 ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7'}"/></svg>`
    b.addEventListener('click', (e) => { e.stopPropagation(); show(at + d) })
    return b
  }
  const prev = go(-1), next = go(1)
  if (row.length > 1) stage.append(prev, next)
  // like Photos: no wrap-around, the arrow at an end is dimmed
  const show = (i: number, slide = 0): void => {
    const to = Math.max(0, Math.min(row.length - 1, i))
    if (to !== at && slide && !matchMedia?.('(prefers-reduced-motion: reduce)').matches) img.animate?.([{ transform: `translateX(${slide * 40}px)`, opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 200, easing: 'cubic-bezier(.2,.8,.2,1)' })
    at = to
    img.src = row[at].src; img.alt = row[at].name
    name.textContent = row[at].name; view.setAttribute('aria-label', row[at].name)
    count.textContent = row.length > 1 ? host.t('nOfTotal', { n: at + 1, total: row.length }) : ''
    count.hidden = row.length < 2
    prev.disabled = at === 0; next.disabled = at === row.length - 1
    pencil.style.visibility = canMark(at) ? '' : 'hidden'
  }
  show(at)

  let marking = false
  view.addEventListener('keydown', (e) => {
    if (marking) return
    if (e.key === 'ArrowRight') { e.preventDefault(); show(at + 1, 1) }
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(at - 1, -1) }
  })
  let x0 = 0, y0 = 0, swiped = false
  stage.addEventListener('pointerdown', (e) => { x0 = e.clientX; y0 = e.clientY })
  stage.addEventListener('pointerup', (e) => {
    const dx = e.clientX - x0
    if (row.length > 1 && Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(e.clientY - y0)) { swiped = true; show(at + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1) }
  })
  const close = (): void => { view.close() }
  x.addEventListener('click', close)
  stage.addEventListener('click', (e) => { if (swiped) { swiped = false; return } if (e.target === stage) close() })   // a tap beside the picture
  view.addEventListener('cancel', (e) => { if (marking) e.preventDefault() })   // Esc in markup leaves markup only (the editor handles it)
  view.addEventListener('close', () => view.remove())

  pencil.addEventListener('click', (e) => {
    e.stopPropagation()
    if (!canMark(at)) return
    const i = at, item = row[i]
    marking = true; view.classList.add('marking')
    openEditor({
      src: item.src, name: item.name, mount: view, t: (k) => host.t(k), shapes: drawn.get(i),
      onDone: (image) => {
        marking = false
        if (host.mark) host.mark(item.el, image, item.name); else legacyEdit?.(image)
        close()
      },
      onCancel: (shapes) => {
        marking = false; view.classList.remove('marking')
        drawn.set(i, shapes)
        pencil.focus({ preventScroll: true })
      },
    })
  })

  host.wrap.append(view)
  if (typeof view.showModal === 'function') view.showModal(); else view.setAttribute('open', '')
  x.focus({ preventScroll: true })
}

/**
 * The image view: an image large over the chat, x or Esc or a tap beside it closes it; the images sent with one
 * message page with arrows, keys and a swipe; an image still in the composer gets the pencil (markup). Loaded the first
 * time an image is opened, with the markup editor (agui-chat.editor.js next to the one-script build).
 */
import { h } from './dom'
import { openEditor } from './editor'

export interface ZoomHost {
  wrap: HTMLElement
  t: (key: string, vars?: Record<string, string | number>) => string
  icon: (el: HTMLElement, name: 'close') => void
}

export function openZoom(host: ZoomHost, opener: HTMLElement, edit?: (image: Blob) => void): void {
  // the images sent with the same message page with \u2039 1 of 2 \u203a, \u2190 / \u2192 and a swipe; one in the composer stays alone
  const own = opener.closest('.att-row')
  const openers = own ? [...own.querySelectorAll<HTMLElement>('.att-open')] : [opener]
  const row = openers.map((b) => ({ src: b.querySelector('img')?.getAttribute('src') ?? '', name: b.getAttribute('aria-label') ?? '' }))
  let at = Math.max(0, openers.indexOf(opener))
  // a modal <dialog>: the browser puts it above everything on the page (no stacking context can cover it), Esc closes it
  const x = h('button', { class: 'zoom-x', type: 'button', 'aria-label': host.t('close') }); host.icon(x, 'close')
  const img = h('img', { src: row[at]?.src, alt: row[at]?.name }) as HTMLImageElement
  // the buttons sit on the picture's corner and the pager under it, not in the corners of the screen
  const fig = h('div', { class: 'zoom-fig' }, img, x)
  // beside the picture's top right corner when there is room (nothing covers it); on it otherwise (a phone)
  const place = (): void => { fig.classList.toggle('out', fig.getBoundingClientRect().right + 52 <= innerWidth) }
  img.addEventListener('load', place)
  addEventListener('resize', place)
  const view = h('dialog', { class: 'zoom', part: 'zoom', 'aria-label': row[at]?.name }, fig) as HTMLDialogElement
  let swiped = false
  if (row.length > 1) {
    const count = h('span', { class: 'zoom-n', 'aria-live': 'polite' })
    const step = (d: number) => {
      const b = h('button', { class: 'zoom-go', type: 'button', 'aria-label': host.t(d < 0 ? 'prevImage' : 'nextImage') })
      b.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d < 0 ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7'}"/></svg>`
      b.addEventListener('click', (e) => { e.stopPropagation(); show(at + d) })
      return b
    }
    const prev = step(-1), next = step(1)
    // like Photos: no wrap-around, the arrow at an end is dimmed
    const show = (i: number): void => {
      at = Math.max(0, Math.min(row.length - 1, i))
      img.src = row[at].src; img.alt = row[at].name; view.setAttribute('aria-label', row[at].name)
      count.textContent = host.t('nOfTotal', { n: at + 1, total: row.length })
      prev.disabled = at === 0; next.disabled = at === row.length - 1
    }
    fig.append(h('div', { class: 'zoom-pager', part: 'zoom-pager' }, prev, count, next))
    show(at)
    view.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') { e.preventDefault(); show(at + 1) }
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(at - 1) }
    })
    let x0 = 0
    view.addEventListener('pointerdown', (e) => { x0 = e.clientX })
    view.addEventListener('pointerup', (e) => { const dx = e.clientX - x0; if (Math.abs(dx) > 40) { swiped = true; show(at + (dx < 0 ? 1 : -1)) } })
  }
  const close = (): void => { view.close() }
  x.addEventListener('click', close)
  view.addEventListener('click', (e) => { if (swiped) { swiped = false; return } if (e.target === view) close() })   // a tap beside the picture
  view.addEventListener('close', () => { view.remove(); removeEventListener('resize', place) })
  // an image still in the composer can be marked up (the editor loads now): Save puts the marked-up copy in its place
  if (edit) {
    const pencil = h('button', { class: 'zoom-x zoom-edit', type: 'button', 'aria-label': host.t('markup') })
    pencil.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20l4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20zM14 7l3 3"/></svg>'
    pencil.addEventListener('click', (e) => {
      e.stopPropagation()
      void Promise.resolve(openEditor).then((open) => {
        img.hidden = true; x.hidden = true; pencil.hidden = true
        open({ src: row[at].src, name: row[at].name, mount: view, t: (k) => host.t(k), onSave: (blob) => { edit(blob); close() }, onClose: close })
      }).catch(() => { pencil.hidden = true })   // no editor file next to the script: the view stays
    })
    fig.append(pencil)
  }
  host.wrap.append(view)
  if (typeof view.showModal === 'function') view.showModal(); else view.setAttribute('open', '')
  requestAnimationFrame(place)
  x.focus({ preventScroll: true })

}

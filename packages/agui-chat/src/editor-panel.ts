/**
 * The tool panel for an image still in the composer, like the editor in the Claude desktop app: one bar under the
 * picture with the pen, a frame and text, a colour, a line width, undo, redo, clear, Save and close. The colour and
 * the line width open a small menu above the bar (Thin, Medium, Thick, Extra thick, the chosen one ticked). Save gives
 * the marked-up image back; close and Esc go back to the picture. A picture already sent is never drawn on.
 * Loaded with the image view; it brings its own styles.
 */
export interface PanelOptions {
  src: string
  name: string
  /** Where the editor goes (the image view). */
  mount: HTMLElement
  t: (key: string) => string
  onSave: (image: Blob) => void
  onClose: () => void
}

import type { Shape } from './editor'

const COLORS = ['#ff3b30', '#ff9500', '#ffcc00', '#34c759', '#0a84ff', '#ffffff', '#1d1d1f']   // the iOS Markup palette
const WIDTHS = [2, 5, 9, 14]   // Thin, Medium, Thick, Extra thick
/** The names of the widths, here and not in the chat's own strings, so they cost the main file nothing. */
const NAMES: Record<string, string[]> = {
  en: ['Thin', 'Medium', 'Thick', 'Extra thick'],
  ru: ['\u0422\u043e\u043d\u043a\u0430\u044f', '\u0421\u0440\u0435\u0434\u043d\u044f\u044f', '\u0422\u043e\u043b\u0441\u0442\u0430\u044f', '\u041e\u0447\u0435\u043d\u044c \u0442\u043e\u043b\u0441\u0442\u0430\u044f'],   // Tonkaya, Srednyaya, Tolstaya, Ochen tolstaya
  uk: ['\u0422\u043e\u043d\u043a\u0430', '\u0421\u0435\u0440\u0435\u0434\u043d\u044f', '\u0422\u043e\u0432\u0441\u0442\u0430', '\u0414\u0443\u0436\u0435 \u0442\u043e\u0432\u0441\u0442\u0430'],   // Tonka, Serednya, Tovsta, Duzhe tovsta
  de: ['D\u00fcnn', 'Mittel', 'Dick', 'Sehr dick'],
  fr: ['Fin', 'Moyen', '\u00c9pais', 'Tr\u00e8s \u00e9pais'],
  es: ['Fino', 'Medio', 'Grueso', 'Muy grueso'],
  it: ['Sottile', 'Medio', 'Spesso', 'Molto spesso'],
}

const ICON: Record<string, string> = {
  pen: 'M4 20l4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20zM14 7l3 3',
  rect: 'M5 5h14v14H5z',
  text: 'M6 6h12M12 6v13M9 19h6',
  undo: 'M9 14 4 9l5-5M4 9h10a6 6 0 0 1 0 12h-3',
  redo: 'M15 14l5-5-5-5M20 9H10a6 6 0 0 0 0 12h3',
  clear: 'M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13M10 11v6M14 11v6',
  close: 'M6 6l12 12M18 6 6 18',
}
const svg = (name: string): string =>
  `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICON[name]}"/></svg>`

const CSS = `
.pk { position: fixed; inset: 0; display: grid; grid-template-rows: minmax(0, 1fr) auto; gap: 16px; padding: 56px 16px max(16px, env(safe-area-inset-bottom, 0px)); cursor: default; }
.pk, .pk * { box-sizing: border-box; }
.pk-stage { position: relative; min-height: 0; }
.pk-stage canvas { position: absolute; inset: 0; margin: auto; max-width: 100%; max-height: 100%; border-radius: 8px; touch-action: none; cursor: crosshair; }
.pk-text { position: absolute; min-width: 40px; padding: 2px 4px; border: 1px dashed currentColor; background: transparent; outline: none; font: 600 20px -apple-system, sans-serif; }
.pk-bar { justify-self: center; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 4px; padding: 6px; border-radius: 18px; max-width: 100%;   /* a phone: two rows, Save always in view */
  background: color-mix(in srgb, black 70%, transparent); -webkit-backdrop-filter: blur(20px) saturate(160%); backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid color-mix(in srgb, white 12%, transparent); }
.pk-bar button { flex: none; min-width: 44px; height: 44px; border: 0; border-radius: 12px; background: none; color: white; display: grid; place-items: center; cursor: pointer; font: inherit; }
.pk-bar button[aria-pressed=true] { background: color-mix(in srgb, white 16%, transparent); color: var(--agui-link, #0a84ff); }
.pk-bar button:disabled { opacity: .35; cursor: default; }
.pk-bar button[aria-expanded=true] { background: color-mix(in srgb, white 16%, transparent); }
.pk-bar button:focus-visible, .pk-menu button:focus-visible { outline: 2px solid var(--agui-link, #0a84ff); outline-offset: -2px; }
.pk-dot { width: 22px; height: 22px; border-radius: 50%; border: 2px solid color-mix(in srgb, white 70%, transparent); }
.pk-line { display: block; width: 26px; border-radius: 99px; background: white; }
.pk-save { padding: 0 16px; background: color-mix(in srgb, white 16%, transparent) !important; font-weight: 500 !important; font-size: 16px !important; }
/* a menu above the bar, over its button: the colours in a row, the line widths as a list with the chosen one ticked */
.pk-menu { position: fixed; z-index: 2; padding: 6px; border-radius: 16px; background: color-mix(in srgb, white 16%, black);
  border: 1px solid color-mix(in srgb, white 12%, transparent); box-shadow: 0 12px 32px -8px black; animation: pk-in .14s ease both; }
.pk-menu.row { display: flex; gap: 2px; }
.pk-menu.list { display: grid; min-width: 220px; }
.pk-menu button { border: 0; background: none; color: white; cursor: pointer; font: inherit; border-radius: 10px; }
.pk-menu.row button { width: 44px; height: 44px; display: grid; place-items: center; }
.pk-menu.list button { display: grid; grid-template-columns: 30px 1fr 22px; align-items: center; gap: 12px; min-height: 44px; padding: 0 12px; text-align: left; font-size: 17px; }
.pk-menu button:hover { background: color-mix(in srgb, white 12%, transparent); }
.pk-menu .tick { color: var(--agui-link, #0a84ff); visibility: hidden; }
.pk-menu [aria-checked=true] .tick { visibility: visible; }
.pk-menu.row [aria-checked=true] .pk-dot { box-shadow: 0 0 0 2px var(--agui-link, #0a84ff); }
@keyframes pk-in { from { opacity: 0; transform: translateY(4px); } }
@media (hover: hover) { .pk-menu.list button { min-height: 40px; font-size: 15px; } }
@media (prefers-reduced-motion: reduce) { .pk-menu { animation: none; } }
`

export function openPanel(o: PanelOptions): void {
  const shapes: Shape[] = []
  const undone: Shape[] = []
  let tool: 'pen' | 'rect' | 'text' = 'pen'
  let color = COLORS[0]
  let width = WIDTHS[1]
  const img = new Image()
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  const stage = document.createElement('div'); stage.className = 'pk-stage'; stage.append(canvas)
  const bar = document.createElement('div'); bar.className = 'pk-bar'; bar.setAttribute('role', 'toolbar')
  const root = document.createElement('div'); root.className = 'pk'
  const style = document.createElement('style'); style.textContent = CSS
  root.append(style, stage, bar)

  const button = (label: string, inner: string, onclick: () => void, cls = ''): HTMLButtonElement => {
    const b = document.createElement('button'); b.type = 'button'; b.className = cls; b.setAttribute('aria-label', label); b.innerHTML = inner
    b.addEventListener('click', (e) => { e.stopPropagation(); onclick() })
    return b
  }

  const draw = (extra?: Shape): void => {
    undo.disabled = !shapes.length; redo.disabled = !undone.length; clear.disabled = !shapes.length
    if (!ctx) return   // no canvas here (a test page): the buttons still follow
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    for (const s of extra ? [...shapes, extra] : shapes) {
      ctx.strokeStyle = s.color; ctx.fillStyle = s.color; ctx.lineCap = 'round'; ctx.lineJoin = 'round'
      if (s.kind === 'pen') {
        ctx.lineWidth = s.width * scale(); ctx.beginPath()
        s.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)))
        ctx.stroke()
      } else if (s.kind === 'rect') {
        ctx.lineWidth = s.width * scale(); ctx.strokeRect(s.x, s.y, s.w, s.h)
      } else {
        ctx.font = `600 ${s.size * scale()}px -apple-system, BlinkMacSystemFont, sans-serif`; ctx.textBaseline = 'top'; ctx.fillText(s.text, s.x, s.y)
      }
    }
    undo.disabled = !shapes.length; redo.disabled = !undone.length; clear.disabled = !shapes.length
  }
  /** Canvas pixels per screen pixel: lines look the same thickness however big the photo is. */
  const scale = (): number => canvas.width / Math.max(1, canvas.getBoundingClientRect().width || canvas.width)
  const at = (e: PointerEvent): [number, number] => {
    const r = canvas.getBoundingClientRect()
    return [((e.clientX - r.left) / r.width) * canvas.width, ((e.clientY - r.top) / r.height) * canvas.height]
  }
  const add = (s: Shape): void => { shapes.push(s); undone.length = 0; draw() }

  let live: Shape | null = null
  canvas.addEventListener('pointerdown', (e) => {
    e.stopPropagation()
    const [x, y] = at(e)
    if (tool === 'text') return void writeAt(e, x, y)
    canvas.setPointerCapture(e.pointerId)
    live = tool === 'pen' ? { kind: 'pen', color, width, pts: [[x, y]] } : { kind: 'rect', color, width, x, y, w: 0, h: 0 }
  })
  canvas.addEventListener('pointermove', (e) => {
    if (!live) return
    const [x, y] = at(e)
    if (live.kind === 'pen') live.pts.push([x, y])
    else if (live.kind === 'rect') { live.w = x - live.x; live.h = y - live.y }
    draw(live)
  })
  const end = (): void => { if (live && (live.kind !== 'rect' || Math.abs(live.w) + Math.abs(live.h) > 4)) add(live); live = null; draw() }
  canvas.addEventListener('pointerup', end)
  canvas.addEventListener('pointercancel', end)
  canvas.addEventListener('click', (e) => e.stopPropagation())

  /** A word on the picture: a field where it was tapped; Enter or leaving it puts the text in. */
  const writeAt = (e: PointerEvent, x: number, y: number): void => {
    const field = document.createElement('input')
    field.className = 'pk-text'; field.style.color = color
    const r = canvas.getBoundingClientRect(), sr = stage.getBoundingClientRect()
    field.style.left = `${e.clientX - sr.left}px`; field.style.top = `${e.clientY - sr.top - 14}px`
    void r
    let done = false
    const put = (): void => {
      if (done) return
      done = true
      const text = field.value.trim()
      field.remove()
      if (text) add({ kind: 'text', color, size: 20 + width * 1.5, x, y: y - 14 * scale(), text })
    }
    field.addEventListener('keydown', (k) => { k.stopPropagation(); if (k.key === 'Enter') put(); if (k.key === 'Escape') { done = true; field.remove() } })
    field.addEventListener('blur', put)
    field.addEventListener('click', (c) => c.stopPropagation())
    stage.append(field)
    setTimeout(() => field.focus(), 0)
  }

  const tools: HTMLButtonElement[] = []
  const pickTool = (t: typeof tool): void => { tool = t; tools.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.tool === t))) }
  for (const t of ['pen', 'rect', 'text'] as const) {
    const b = button(o.t(t), svg(t), () => pickTool(t)); b.dataset.tool = t; tools.push(b)
  }
  // ---- the two menus above the bar (one at a time): a tap on its button, outside or Esc closes it; arrows move
  let menu: { el: HTMLElement; from: HTMLButtonElement } | null = null
  const shutMenu = (focus = false): void => { if (!menu) return; const { el, from } = menu; menu = null; el.remove(); from.setAttribute('aria-expanded', 'false'); if (focus) from.focus({ preventScroll: true }) }
  const openMenu = (from: HTMLButtonElement, kind: 'row' | 'list', items: HTMLButtonElement[]): void => {
    if (menu?.from === from) return shutMenu(true)
    shutMenu()
    const el = document.createElement('div'); el.className = `pk-menu ${kind}`; el.setAttribute('role', 'menu'); el.setAttribute('aria-label', from.getAttribute('aria-label') ?? '')
    el.append(...items)
    el.addEventListener('keydown', (k) => {
      const i = items.indexOf((root.getRootNode() as ShadowRoot | Document).activeElement as HTMLButtonElement)
      const d = k.key === 'ArrowDown' || k.key === 'ArrowRight' ? 1 : k.key === 'ArrowUp' || k.key === 'ArrowLeft' ? -1 : 0
      if (d) { k.preventDefault(); k.stopPropagation(); items[(i + d + items.length) % items.length].focus() }
    })
    root.append(el)
    const b = from.getBoundingClientRect(), w = el.offsetWidth, vw = root.getBoundingClientRect().width || innerWidth
    el.style.left = `${Math.max(8, Math.min(vw - w - 8, b.left + b.width / 2 - w / 2))}px`
    el.style.bottom = `${innerHeight - b.top + 14}px`
    from.setAttribute('aria-expanded', 'true')
    menu = { el, from }
    ;(items.find((x) => x.getAttribute('aria-checked') === 'true') ?? items[0]).focus({ preventScroll: true })
  }
  const option = (label: string, inner: string, on: boolean, pick: () => void): HTMLButtonElement => {
    const b = button(label, inner, () => { pick(); shutMenu(true) })
    b.setAttribute('role', 'menuitemradio'); b.setAttribute('aria-checked', String(on))
    return b
  }
  const dot = document.createElement('span'); dot.className = 'pk-dot'; dot.style.background = color
  const colorBtn = button(o.t('colour'), '', () => openMenu(colorBtn, 'row', COLORS.map((c) =>
    option(c, `<span class="pk-dot" style="background:${c}"></span>`, c === color, () => { color = c; dot.style.background = c }))))
  colorBtn.append(dot); colorBtn.setAttribute('aria-haspopup', 'menu'); colorBtn.setAttribute('aria-expanded', 'false')
  const names = NAMES[String((o.mount.getRootNode() as ShadowRoot).host?.getAttribute?.('lang') ?? ((o.mount.getRootNode() as ShadowRoot).host as { lang?: string } | undefined)?.lang ?? 'en')] ?? NAMES.en
  const sample = (w: number): string => `<span class="pk-line" style="height:${Math.max(2, Math.round(w * 0.9))}px"></span>`
  const TICK = '<svg class="tick" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5 10 17.5 19 7"/></svg>'
  const line = document.createElement('span'); line.className = 'pk-line'; line.style.height = `${Math.max(2, Math.round(width * 0.9))}px`
  const widthBtn = button(o.t('lineWidth'), '', () => openMenu(widthBtn, 'list', WIDTHS.map((w, i) =>
    option(names[i], `${sample(w)}<span>${names[i]}</span>${TICK}`, w === width, () => { width = w; line.style.height = `${Math.max(2, Math.round(w * 0.9))}px` }))))
  widthBtn.append(line); widthBtn.setAttribute('aria-haspopup', 'menu'); widthBtn.setAttribute('aria-expanded', 'false')
  const undo = button(o.t('undo'), svg('undo'), () => { const s = shapes.pop(); if (s) undone.push(s); draw() })
  const redo = button(o.t('redo'), svg('redo'), () => { const s = undone.pop(); if (s) shapes.push(s); draw() })
  const clear = button(o.t('clearAll'), svg('clear'), () => { undone.push(...shapes.splice(0).reverse()); draw() })
  const save = button(o.t('save'), o.t('save'), () => {
    canvas.toBlob((blob) => { if (blob) { root.remove(); o.onSave(blob) } }, 'image/png')
  }, 'pk-save')
  const shut = (): void => { root.remove(); o.onClose() }
  const close = button(o.t('close'), svg('close'), shut)
  bar.append(...tools, colorBtn, widthBtn, undo, redo, clear, save, close)
  pickTool('pen')

  img.onload = () => {
    canvas.width = img.naturalWidth; canvas.height = img.naturalHeight
    draw()
  }
  img.src = o.src
  root.addEventListener('click', (e) => { e.stopPropagation(); if (menu && !menu.el.contains(e.target as Node) && !menu.from.contains(e.target as Node)) shutMenu() })   // taps in the editor never close the image view; one outside a menu closes the menu
  canvas.addEventListener('pointerdown', () => shutMenu(), true)
  const onKey = (e: KeyboardEvent): void => {
    if (!root.isConnected) return void o.mount.removeEventListener('keydown', onKey)
    if (e.key === 'Escape' && menu) { e.preventDefault(); e.stopPropagation(); shutMenu(true); return }   // the menu first, then the editor
    if (e.key === 'Escape' && !(e.target as HTMLElement).matches?.('.pk-text')) { e.preventDefault(); shut() }
  }
  o.mount.addEventListener('keydown', onKey)
  o.mount.append(root)
  tools[0].focus({ preventScroll: true })
}

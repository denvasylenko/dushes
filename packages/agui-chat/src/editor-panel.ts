/**
 * The tool panel for an image still in the composer, like the editor in the Claude desktop app: one bar under the
 * picture with the pen, a frame and text, a colour, a line width, undo, redo, clear, Save and close. Save gives the
 * marked-up image back; close and Esc go back to the picture. (A sent picture gets the phone-style markup, editor.ts.)
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
const WIDTHS = [3, 6, 12]

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
@media (max-width: 520px) { .pk-bar .pk-sep { display: none; } }
.pk-bar .pk-sep { width: 1px; height: 24px; margin: 0 4px; background: color-mix(in srgb, white 18%, transparent); }
.pk-dot { width: 22px; height: 22px; border-radius: 50%; border: 2px solid color-mix(in srgb, white 70%, transparent); }
.pk-line { width: 26px; border-radius: 99px; background: white; }
.pk-save { padding: 0 18px; background: white !important; color: black !important; font-weight: 600 !important; border-radius: 99px !important; }
.pk-pop { display: flex; gap: 6px; padding: 0 4px; }
.pk-pop[hidden] { display: none; }
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
  const sep = (): HTMLElement => { const s = document.createElement('span'); s.className = 'pk-sep'; return s }

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
  const dot = document.createElement('span'); dot.className = 'pk-dot'; dot.style.background = color
  const colors = document.createElement('span'); colors.className = 'pk-pop'; colors.hidden = true
  for (const c of COLORS) {
    const b = button(c, `<span class="pk-dot" style="background:${c}"></span>`, () => { color = c; dot.style.background = c; colors.hidden = true })
    colors.append(b)
  }
  const colorBtn = button(o.t('colour'), '', () => { colors.hidden = !colors.hidden }); colorBtn.append(dot)
  const line = document.createElement('span'); line.className = 'pk-line'; line.style.height = `${width}px`
  const widthBtn = button(o.t('lineWidth'), '', () => { width = WIDTHS[(WIDTHS.indexOf(width) + 1) % WIDTHS.length]; line.style.height = `${width}px` }); widthBtn.append(line)
  const undo = button(o.t('undo'), svg('undo'), () => { const s = shapes.pop(); if (s) undone.push(s); draw() })
  const redo = button(o.t('redo'), svg('redo'), () => { const s = undone.pop(); if (s) shapes.push(s); draw() })
  const clear = button(o.t('clearAll'), svg('clear'), () => { undone.push(...shapes.splice(0).reverse()); draw() })
  const save = button(o.t('save'), o.t('save'), () => {
    canvas.toBlob((blob) => { if (blob) { root.remove(); o.onSave(blob) } }, 'image/png')
  }, 'pk-save')
  const shut = (): void => { root.remove(); o.onClose() }
  const close = button(o.t('close'), svg('close'), shut)
  bar.append(...tools, sep(), colorBtn, colors, widthBtn, sep(), undo, redo, clear, save, close)
  pickTool('pen')

  img.onload = () => {
    canvas.width = img.naturalWidth; canvas.height = img.naturalHeight
    draw()
  }
  img.src = o.src
  root.addEventListener('click', (e) => e.stopPropagation())   // taps in the editor never close the image view
  const onKey = (e: KeyboardEvent): void => {
    if (!root.isConnected) return void o.mount.removeEventListener('keydown', onKey)
    if (e.key === 'Escape' && !(e.target as HTMLElement).matches?.('.pk-text')) { e.preventDefault(); shut() }
  }
  o.mount.addEventListener('keydown', onKey)
  o.mount.append(root)
  tools[0].focus({ preventScroll: true })
}

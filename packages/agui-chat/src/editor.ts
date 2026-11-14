/**
 * Markup over an image, like the Claude app and iOS Markup: draw with a finger or the mouse. On top: x (back to the
 * picture, the drawing kept while the view is open), undo and redo, and one check mark that gives the marked-up copy
 * back. At the bottom: one round tool button (the pen in its colour) that opens the tools (pen, frame, text) and the
 * colours. Loaded with the image view (agui-chat.editor.js next to the one-script build); its styles are its own.
 */
export interface EditorOptions {
  src: string
  name: string
  /** Where the editor goes (the image view). */
  mount: HTMLElement
  t: (key: string) => string
  /** What was drawn before on this image (x keeps it while the view is open). */
  shapes?: Shape[]
  /** The check mark: the marked-up copy (PNG). */
  onDone: (image: Blob) => void
  /** x, Esc, or the check mark with nothing drawn: back to the picture with what was drawn so far. */
  onCancel: (shapes: Shape[]) => void
}

export type Shape =
  | { kind: 'pen'; color: string; width: number; pts: [number, number][] }
  | { kind: 'rect'; color: string; width: number; x: number; y: number; w: number; h: number }
  | { kind: 'text'; color: string; size: number; x: number; y: number; text: string }

// the iOS Markup palette, each with its name for the screen reader
const COLORS: [string, string][] = [['#ff3b30', 'colourRed'], ['#ffcc00', 'colourYellow'], ['#34c759', 'colourGreen'], ['#0a84ff', 'colourBlue'], ['#ffffff', 'colourWhite'], ['#1d1d1f', 'colourBlack']]
const WIDTH = 4   // screen pixels, whatever the photo's size

const ICON: Record<string, string> = {
  pen: 'M4 20l4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20zM14 7l3 3',
  rect: 'M5 5h14v14H5z',
  text: 'M6 6h12M12 6v13M9 19h6',
  undo: 'M9 14 4 9l5-5M4 9h10a6 6 0 0 1 0 12h-3',
  redo: 'M15 14l5-5-5-5M20 9H10a6 6 0 0 0 0 12h3',
  close: 'M6 6l12 12M18 6 6 18',
  done: 'M5 12.5l4.5 4.5L19 7.5',
}
const svg = (name: string, w = 1.8): string =>
  `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICON[name]}"/></svg>`
// the tool button: a pencil standing up, its tip and band in the colour
const TOOL = (c: string): string =>
  `<svg viewBox="0 0 24 40" width="18" height="32" aria-hidden="true"><path d="M12 2 7 14v24h10V14z" fill="#e5e5ea"/><path d="M12 2 9.6 8h4.8z" fill="${c}"/><rect x="7" y="27" width="10" height="3" fill="${c}"/></svg>`

const CSS = `
.mk { position: fixed; inset: 0; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; cursor: default; color: white; }
.mk, .mk * { box-sizing: border-box; }
.mk-top { display: grid; grid-template-columns: 44px 1fr 44px; align-items: center; gap: 12px; padding: max(10px, env(safe-area-inset-top, 0px)) 12px 10px; }
.mk-hist { justify-self: center; display: flex; gap: 2px; padding: 0 4px; height: 44px; align-items: center; border-radius: 22px;
  background: color-mix(in srgb, white 14%, transparent); -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
.mk-hist button { width: 44px; height: 44px; border: 0; border-radius: 50%; background: none; color: white; display: grid; place-items: center; cursor: pointer; padding: 0; }
.mk-hist button:disabled { opacity: .35; cursor: default; }
.mk-hist button:focus-visible { outline: 2px solid var(--agui-accent); outline-offset: -2px; }
.mk-round:disabled { opacity: .35; cursor: default; }
.mk-done { background: white; color: black; }
.mk-done:hover:not(:disabled) { background: color-mix(in srgb, white 86%, black); }
.mk-stage { position: relative; min-height: 0; }
/* the photo's own pixels, shown fitted and centred like in the view (absolute: a big canvas cannot widen the page) */
.mk-stage canvas { position: absolute; inset: 0 16px; margin: auto; max-width: calc(100% - 32px); max-height: 100%; border-radius: var(--agui-radius-sm); touch-action: none; cursor: crosshair; }
.mk-text { position: absolute; min-width: 40px; padding: 2px 4px; border: 1px dashed currentColor; border-radius: 4px; background: transparent; outline: none; font: 600 20px -apple-system, BlinkMacSystemFont, sans-serif; }
.mk-foot { position: relative; display: flex; align-items: center; padding: 12px 16px max(16px, env(safe-area-inset-bottom, 0px)); }
.mk-tool { width: 56px; height: 56px; border: 0; border-radius: 50%; display: grid; place-items: center; cursor: pointer; padding: 0; flex: none;
  background: color-mix(in srgb, white 16%, transparent); -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); transition: transform .15s; }
.mk-tool:active { transform: scale(.94); }
.mk-tool[aria-expanded=true] { background: color-mix(in srgb, white 26%, transparent); }
.mk-tool:focus-visible { outline: 2px solid var(--agui-accent); outline-offset: 2px; }
/* the tools over the colours, rising from the tool button (it fits a phone: six 44 px colours in a row) */
.mk-pal { position: absolute; left: 16px; bottom: calc(100% - 4px); display: grid; grid-template-columns: repeat(6, 44px); gap: 4px; padding: 8px; border-radius: 22px;
  background: color-mix(in srgb, #1c1c1e 88%, transparent); -webkit-backdrop-filter: blur(20px) saturate(160%); backdrop-filter: blur(20px) saturate(160%);
  box-shadow: 0 10px 30px -10px black; animation: mk-in .18s var(--agui-ease, ease) both; transform-origin: bottom left; }
.mk-pal[hidden] { display: none; }
.mk-pal button { flex: none; width: 44px; height: 44px; border: 0; border-radius: 50%; background: none; color: white; display: grid; place-items: center; cursor: pointer; padding: 0; }
.mk-pal button[aria-pressed=true] { background: color-mix(in srgb, white 20%, transparent); }
.mk-sep { grid-column: 1 / -1; height: 1px; margin: 2px 4px; background: color-mix(in srgb, white 16%, transparent); }
.mk-dot { width: 24px; height: 24px; border-radius: 50%; box-shadow: inset 0 0 0 1.5px color-mix(in srgb, white 40%, transparent); }
.mk-pal button[aria-pressed=true] .mk-dot { box-shadow: 0 0 0 2px #1c1c1e, 0 0 0 4px white; }
@keyframes mk-in { from { opacity: 0; transform: scale(.9); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .mk-pal, .mk-tool { animation: none; transition: none; } }
`

export function openEditor(o: EditorOptions): void {
  const shapes: Shape[] = [...(o.shapes ?? [])]
  const undone: Shape[] = []
  let tool: 'pen' | 'rect' | 'text' = 'pen'
  let color = COLORS[0][0]
  const img = new Image()
  const canvas = document.createElement('canvas')
  canvas.setAttribute('aria-label', `${o.t('markup')}: ${o.name}`)
  const ctx = canvas.getContext('2d')
  const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls: string): HTMLElementTagNameMap[K] => { const e = document.createElement(tag); e.className = cls; return e }
  const button = (label: string, inner: string, onclick: () => void, cls = ''): HTMLButtonElement => {
    const b = el('button', cls); b.type = 'button'; b.setAttribute('aria-label', label); b.innerHTML = inner
    b.addEventListener('click', (e) => { e.stopPropagation(); onclick() })
    return b
  }

  const root = el('div', 'mk')
  const style = document.createElement('style'); style.textContent = CSS
  const stage = el('div', 'mk-stage'); stage.append(canvas)

  /** Canvas pixels per screen pixel: lines look the same thickness however big the photo is. */
  const scale = (): number => canvas.width / Math.max(1, canvas.getBoundingClientRect().width || canvas.width)
  const draw = (extra?: Shape): void => {
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    if (img.naturalWidth) ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    for (const s of extra ? [...shapes, extra] : shapes) {
      ctx.strokeStyle = s.color; ctx.fillStyle = s.color; ctx.lineCap = 'round'; ctx.lineJoin = 'round'
      if (s.kind === 'pen') {
        ctx.lineWidth = s.width; ctx.beginPath()
        s.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)))
        if (s.pts.length === 1) ctx.lineTo(s.pts[0][0] + 0.1, s.pts[0][1])   // a tap leaves a dot
        ctx.stroke()
      } else if (s.kind === 'rect') {
        ctx.lineWidth = s.width; ctx.strokeRect(s.x, s.y, s.w, s.h)
      } else {
        ctx.font = `600 ${s.size}px -apple-system, BlinkMacSystemFont, sans-serif`; ctx.textBaseline = 'top'; ctx.fillText(s.text, s.x, s.y)
      }
    }
  }
  const sync = (): void => { undo.disabled = !shapes.length; redo.disabled = !undone.length }
  const at = (e: PointerEvent): [number, number] => {
    const r = canvas.getBoundingClientRect()
    return [((e.clientX - r.left) / r.width) * canvas.width, ((e.clientY - r.top) / r.height) * canvas.height]
  }
  const add = (s: Shape): void => { shapes.push(s); undone.length = 0; draw(); sync() }

  let live: Shape | null = null
  canvas.addEventListener('pointerdown', (e) => {
    e.stopPropagation()
    pal.hidden = true; toolBtn.setAttribute('aria-expanded', 'false')   // drawing puts the tools away
    const [x, y] = at(e)
    if (tool === 'text') return void writeAt(e, x, y)
    canvas.setPointerCapture?.(e.pointerId)
    const w = WIDTH * scale()
    live = tool === 'pen' ? { kind: 'pen', color, width: w, pts: [[x, y]] } : { kind: 'rect', color, width: w * 0.8, x, y, w: 0, h: 0 }
  })
  canvas.addEventListener('pointermove', (e) => {
    if (!live) return
    for (const ev of (e.getCoalescedEvents?.() ?? [e])) {   // every sample the finger gave: smooth curves
      const [x, y] = at(ev)
      if (live.kind === 'pen') live.pts.push([x, y])
      else if (live.kind === 'rect') { live.w = x - live.x; live.h = y - live.y }
    }
    draw(live)
  })
  const end = (): void => { if (live && (live.kind !== 'rect' || Math.abs(live.w) + Math.abs(live.h) > 4)) add(live); live = null; draw() }
  canvas.addEventListener('pointerup', end)
  canvas.addEventListener('pointercancel', end)

  /** A word on the picture: a field where it was tapped; Enter or leaving it puts the text in. */
  const writeAt = (e: PointerEvent, x: number, y: number): void => {
    const field = el('input', 'mk-text')
    field.style.color = color
    const sr = stage.getBoundingClientRect()
    field.style.left = `${e.clientX - sr.left}px`; field.style.top = `${e.clientY - sr.top - 14}px`
    let done = false
    const put = (): void => {
      if (done) return
      done = true
      const text = field.value.trim()
      field.remove()
      if (text) add({ kind: 'text', color, size: 22 * scale(), x, y: y - 14 * scale(), text })
    }
    field.addEventListener('keydown', (k) => { k.stopPropagation(); if (k.key === 'Enter') put(); if (k.key === 'Escape') { done = true; field.remove() } })
    field.addEventListener('blur', put)
    field.addEventListener('click', (c) => c.stopPropagation())
    stage.append(field)
    setTimeout(() => field.focus(), 0)
  }

  // the top bar: x, undo / redo, the check mark
  const cancel = (): void => { root.remove(); o.onCancel(shapes) }
  const close = button(o.t('markupCancel'), svg('close'), cancel, 'mk-round')
  const undo = button(o.t('undo'), svg('undo'), () => { const s = shapes.pop(); if (s) undone.push(s); draw(); sync() })
  const redo = button(o.t('redo'), svg('redo'), () => { const s = undone.pop(); if (s) shapes.push(s); draw(); sync() })
  const hist = el('div', 'mk-hist'); hist.append(undo, redo)
  const done = button(o.t('markupDone'), svg('done', 2.4), () => {
    if (!shapes.length) return cancel()   // nothing drawn: nothing to send
    done.disabled = true
    canvas.toBlob((blob) => { if (blob) { root.remove(); o.onDone(blob) } else done.disabled = false }, 'image/png')
  }, 'mk-round mk-done')
  const top = el('div', 'mk-top'); top.append(close, hist, done)

  // the bottom: one tool button; the tools and colours beside it
  const pal = el('div', 'mk-pal'); pal.hidden = true; pal.setAttribute('role', 'toolbar'); pal.setAttribute('aria-label', o.t('colour'))
  const toolBtn = button(`${o.t('pen')}, ${o.t('colour')}`, TOOL(color), () => {
    pal.hidden = !pal.hidden; toolBtn.setAttribute('aria-expanded', String(!pal.hidden))
  }, 'mk-tool')
  toolBtn.setAttribute('aria-expanded', 'false')
  const tools: HTMLButtonElement[] = []
  const pickTool = (t: typeof tool): void => {
    tool = t; tools.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.tool === t)))
    toolBtn.setAttribute('aria-label', `${o.t(t)}, ${o.t('colour')}`)
  }
  for (const t of ['pen', 'rect', 'text'] as const) { const b = button(o.t(t), svg(t), () => pickTool(t)); b.dataset.tool = t; tools.push(b) }
  const dots = COLORS.map(([c, key]) => {
    const b = button(o.t(key), `<span class="mk-dot" style="background:${c}"></span>`, () => {
      color = c; toolBtn.innerHTML = TOOL(c); dots.forEach((d) => d.setAttribute('aria-pressed', String(d === b)))
    })
    b.setAttribute('aria-pressed', String(c === color))
    return b
  })
  const sep = el('span', 'mk-sep')
  pal.append(...tools, sep, ...dots)
  pickTool('pen')
  const foot = el('div', 'mk-foot'); foot.append(toolBtn, pal)

  root.append(style, top, stage, foot)
  root.addEventListener('click', (e) => e.stopPropagation())   // taps in the editor never close the image view
  // Esc leaves markup only (the view stays); the listener is on the view, where the key lands when nothing has focus
  const onKey = (e: KeyboardEvent): void => {
    if (!root.isConnected) return void o.mount.removeEventListener('keydown', onKey)
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cancel() }
  }
  o.mount.addEventListener('keydown', onKey)
  sync()

  img.onload = () => { canvas.width = img.naturalWidth; canvas.height = img.naturalHeight; draw() }
  img.src = o.src
  o.mount.append(root)
  close.focus({ preventScroll: true })
}

// the one-script build: register on window.AguiChat (agui-chat.editor.js loads after agui-chat.iife.js)
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.openEditor = openEditor

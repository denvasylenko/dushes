/** Small DOM helpers shared by the chat and by renderers (custom renderers can use them too). */

type Child = Node | string | number | false | null | undefined | Child[]
type Props = Record<string, unknown> & { class?: string; style?: string | Partial<CSSStyleDeclaration> }

/** h('button', {class: 'chip', onclick: fn}, 'Text') -> an element. `on*` props become listeners. */
export function h<K extends keyof HTMLElementTagNameMap>(tag: K, props?: Props | null, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag)
  for (const [k, v] of Object.entries(props ?? {})) {
    if (v === undefined || v === null || v === false) continue
    if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v as EventListener)
    else if (k === 'class') el.className = String(v)
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v)
    else if (k in el && k !== 'list' && k !== 'form') (el as unknown as Record<string, unknown>)[k] = v
    else el.setAttribute(k, v === true ? '' : String(v))
  }
  append(el, children)
  return el
}

function append(el: Node, children: Child[]): void {
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue
    if (Array.isArray(c)) append(el, c)
    else el.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)))
  }
}

export const esc = (s: unknown): string =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)

/** Inline markdown only (`code`, **bold**, *italic*, links), for one-line texts such as card questions. */
export const mdInline = (s: string): string => esc(s)
  .replace(/`([^`]+)`/g, '<code>$1</code>')
  .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
  .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>')
  .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')

/** Minimal markdown: paragraphs, line breaks, **bold**, *italic*, `code`, [links](https://...), "- " lists and
 *  fenced code blocks (```lang, or ```lang title="file") with a copy button. An unclosed fence (text still streaming)
 *  is shown as code too. */
export function md(src: string, labels: { copy?: string } = {}): string {
  const inline = mdInline
  const out: string[] = []
  let list: string[] | null = null
  let para: string[] = []
  let code: string[] | null = null
  let lang = ''
  let title = ''
  const flushPara = () => { if (para.length) out.push(`<p>${para.map(inline).join('<br>')}</p>`); para = [] }
  const flushList = () => { if (list) out.push(`<ul>${list.map((x) => `<li>${inline(x)}</li>`).join('')}</ul>`); list = null }
  const flushCode = () => {
    if (!code) return
    const label = title || lang
    out.push(`<div class="code" part="code"${label ? ` data-lang="${esc(label)}"` : ''}>`
      + `<button type="button" class="code-copy" data-copy data-keep>${esc(labels.copy ?? 'Copy')}</button>`
      + `<pre><code>${esc(code.join('\n'))}</code></pre></div>`)
    code = null
  }
  for (const line of String(src).split('\n')) {
    // an info string may carry attributes after the language: ```yaml title="formguide.yaml"
    const fence = line.match(/^\s*```\s*([\w+#.-]*)(?:\s+(.*?))?\s*$/)
    if (code) {
      if (fence && !fence[1] && !fence[2]) { flushCode(); continue }
      code.push(line)
      continue
    }
    if (fence) {
      flushPara(); flushList(); code = []; lang = fence[1]
      title = (fence[2] ?? '').match(/title=["']?([^"']+)["']?/)?.[1] ?? ''
      continue
    }
    const item = line.match(/^\s*(?:[-*\u2022]|\d+[.)])\s+(.*)$/)
    if (item) { flushPara(); (list ??= []).push(item[1]); continue }
    if (!line.trim()) { flushPara(); flushList(); continue }
    flushList()
    para.push(line)
  }
  flushPara(); flushList(); flushCode()
  return out.join('')
}

export const reducedMotion = (): boolean =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** A height change that eases instead of jumping: `change` runs, then the element moves from its old height to
 *  the new one in 200 ms (at once with reduced motion). */
export function easeHeight(el: HTMLElement | null, change: () => void, ms = 200): void {
  const from = el?.isConnected && !reducedMotion() ? el.offsetHeight : -1
  change()
  if (!el || from < 0 || typeof el.animate !== 'function') return
  const to = el.offsetHeight
  // max-height too: a folded message is held by it (.clamped), and it would win over height
  if (from !== to) el.animate([{ height: `${from}px`, maxHeight: `${from}px`, overflow: 'hidden' }, { height: `${to}px`, maxHeight: `${to}px`, overflow: 'hidden' }], { duration: ms, easing: 'cubic-bezier(.2,.8,.2,1)' })
}

export function store<T>(key: string): { get(): T | null; set(v: T): void } {
  return {
    get() { try { return JSON.parse(localStorage.getItem(key) ?? 'null') } catch { return null } },
    set(v) { try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* private mode */ } },
  }
}

const CHEVRON = (d: string) => `<svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`

/** A number input with an Apple-style stepper: two halves on the right edge, full height, chevrons up and down.
 * The browser's own spin buttons are hidden (styles.ts); typing still works. Returns the wrapper. */
export function numberBox(input: HTMLInputElement, labels: { up: string; down: string } = { up: '+', down: '-' }): HTMLElement {
  const nudge = (dir: 1 | -1) => {
    try { if (dir > 0) input.stepUp(); else input.stepDown() } catch {
      const step = Number(input.step) || 1
      input.value = String((Number(input.value) || 0) + dir * step)
    }
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
  }
  const btn = (dir: 1 | -1) => {
    const b = h('button', { type: 'button', class: 'num-b', tabindex: -1, 'aria-label': dir > 0 ? labels.up : labels.down,
      onclick: () => { nudge(dir); input.focus({ preventScroll: true }) } })
    b.innerHTML = CHEVRON(dir > 0 ? 'M3 7.5 6 4.5l3 3' : 'M3 4.5 6 7.5l3-3')
    return b
  }
  input.addEventListener('keydown', (e) => {   // arrows step like the native control did
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); nudge(e.key === 'ArrowUp' ? 1 : -1) }
  })
  return h('div', { class: 'num' }, input, h('div', { class: 'num-step' }, btn(1), btn(-1)))
}

/** A select with its own chevron (the native arrow is hidden), matching the inputs. */
export function selectBox(select: HTMLSelectElement): HTMLElement {
  return h('div', { class: 'sel' }, select)
}


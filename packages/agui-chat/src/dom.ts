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
 *  fenced code blocks (```lang) with a copy button. An unclosed fence (text still streaming) is shown as code too. */
export function md(src: string, labels: { copy?: string } = {}): string {
  const inline = mdInline
  const out: string[] = []
  let list: string[] | null = null
  let para: string[] = []
  let code: string[] | null = null
  let lang = ''
  const flushPara = () => { if (para.length) out.push(`<p>${para.map(inline).join('<br>')}</p>`); para = [] }
  const flushList = () => { if (list) out.push(`<ul>${list.map((x) => `<li>${inline(x)}</li>`).join('')}</ul>`); list = null }
  const flushCode = () => {
    if (!code) return
    out.push(`<div class="code" part="code"${lang ? ` data-lang="${esc(lang)}"` : ''}>`
      + `<button type="button" class="code-copy" data-copy data-keep>${esc(labels.copy ?? 'Copy')}</button>`
      + `<pre><code>${esc(code.join('\n'))}</code></pre></div>`)
    code = null
  }
  for (const line of String(src).split('\n')) {
    const fence = line.match(/^\s*```\s*([\w+#.-]*)\s*$/)
    if (code) {
      if (fence && !fence[1]) { flushCode(); continue }
      code.push(line)
      continue
    }
    if (fence) { flushPara(); flushList(); code = []; lang = fence[1]; continue }
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

export function store<T>(key: string): { get(): T | null; set(v: T): void } {
  return {
    get() { try { return JSON.parse(localStorage.getItem(key) ?? 'null') } catch { return null } },
    set(v) { try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* private mode */ } },
  }
}

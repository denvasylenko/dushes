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

/** Minimal markdown: paragraphs, line breaks, **bold**, *italic*, `code`, [links](https://...) and "- " lists. */
export function md(src: string): string {
  const inline = (s: string) => esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
  const out: string[] = []
  let list: string[] | null = null
  let para: string[] = []
  const flushPara = () => { if (para.length) out.push(`<p>${para.map(inline).join('<br>')}</p>`); para = [] }
  const flushList = () => { if (list) out.push(`<ul>${list.map((x) => `<li>${inline(x)}</li>`).join('')}</ul>`); list = null }
  for (const line of String(src).split('\n')) {
    const item = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/)
    if (item) { flushPara(); (list ??= []).push(item[1]); continue }
    if (!line.trim()) { flushPara(); flushList(); continue }
    flushList()
    para.push(line)
  }
  flushPara(); flushList()
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

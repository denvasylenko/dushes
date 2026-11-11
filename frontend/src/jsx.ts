import type { JsxNode } from './types'

const TOKEN = /<\s*(\/)?\s*([A-Za-z][\w.]*)([^>]*?)(\/)?\s*>|([^<]+)/g
const NAME = /\bname\s*=\s*(?:"([^"]*)"|'([^']*)')/

/** A tiny JSX-string parser: tags, the `name` attribute and text. */
export function parseJsx(src: string): JsxNode {
  const root: JsxNode = { tag: '#root', name: '#root', children: [] }
  const stack: JsxNode[] = [root]
  let counter = 0
  for (const m of src.matchAll(TOKEN)) {
    const [, closing, tag, attrs, selfClose, text] = m
    const top = stack[stack.length - 1]
    if (text !== undefined) {
      const t = text.replace(/\s+/g, ' ').trim()
      if (t) top.children.push({ tag: '#text', name: `_text_${++counter}`, children: [], text: t })
      continue
    }
    if (closing) {
      if (stack.length > 1 && top.tag === tag) stack.pop()
      continue
    }
    const nm = NAME.exec(attrs ?? '')
    const node: JsxNode = { tag, name: nm ? (nm[1] ?? nm[2]) : `_${tag}_${++counter}`, children: [] }
    top.children.push(node)
    if (!selfClose) stack.push(node)
  }
  return root.children[0] ?? root
}

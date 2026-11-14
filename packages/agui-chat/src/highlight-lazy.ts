/** The field highlight from the chat's own bundle without its code in it: the first call loads the module
 *  (≈ 2 KB) and runs it. The cancel function works before the module is here too. */
import { loadHighlight } from '#highlight-loader'
import type { HighlightOptions } from './highlight'

export function highlightField(target: string | HTMLElement, opts?: HighlightOptions): () => void {
  let cancel: (() => void) | null = null, dead = false
  void loadHighlight().then((m) => { if (!dead) cancel = m.highlightField(target, opts) }).catch(() => {})
  return () => { dead = true; cancel?.() }
}

/** "Look here": the field ringed, scrolled to, focused, with the agent's hint. */
export function lookAt(name: string, hint = ''): void { highlightField(name, { kind: 'look', hint }) }

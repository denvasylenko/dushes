/**
 * Cards from blocks without the blocks in the bundle: a card is drawn at once when the blocks are here (always with
 * a bundler; in the one-script build once agui-chat.blocks.js has arrived), otherwise its empty element is shown and
 * filled in place when the file arrives, so chat.updateCard, registerCard and a host's own renderer keep the element.
 */
import { h } from '../dom'
import { blocksNow, loadBlocks, type Blocks } from '#blocks-loader'
import type { Interrupt, RendererContext } from '../types'
import { blocksShell } from './blocks-base'
import { FG_STRINGS } from './i18n'
import { PACKS } from '../langs'
import type { OnAction } from './blocks'

type Answer = Parameters<Blocks['blocksCard']>[2]

/** Draw into `box` now, or when the blocks arrive; a file that failed to load leaves a Try again in the box. */
export function withBlocks(box: HTMLElement, c: Pick<RendererContext, 't'>, draw: (b: Blocks) => void): HTMLElement {
  const now = blocksNow()
  if (now) { draw(now); return box }
  const go = (): void => {
    box.replaceChildren(); box.setAttribute('aria-busy', 'true'); box.classList.add('bk-wait')   // its room kept: nothing jumps
    void loadBlocks().then((b) => { box.removeAttribute('aria-busy'); box.classList.remove('bk-wait'); draw(b) }, () => {
      box.removeAttribute('aria-busy')
      box.replaceChildren(h('div', { class: 'muted err-line', role: 'alert' }, c.t('error')),
        h('button', { class: 'btn link', type: 'button', onclick: go }, c.t('retry')))
    })
  }
  go()
  return box
}

/** Load the blocks ahead of the first card (a no-op with a bundler). */
export const preloadBlocks = (): Promise<void> => loadBlocks().then(() => undefined)

/**
 * The blocks, for a card renderer of your own (chat.renderers.set): compose with the same parts and theme. Returns
 * the card element at once; in the one-script build its blocks are drawn into it as soon as agui-chat.blocks.js is
 * here (at once after the first card, or after `await AguiChat.loadBlocks()`).
 */
export function blocksCard(it: Interrupt | Record<string, unknown>, c: RendererContext, answer: Answer, onAction?: OnAction): HTMLElement {
  const card = blocksShell(it)
  const ctx = withCardTexts(c)
  return withBlocks(card, ctx, (b) => { b.blocksCard(it, ctx, answer, onAction, card) })
}

/** A host's own context (\`t: chat.t\`, without the formguide plugin) still gets the cards' texts ("Apple Calendar",
 *  "Show data"): a key the chat does not know is looked up in the formguide strings, in the chat's language. */
function withCardTexts(c: RendererContext): RendererContext {
  const t = (key: string, vars?: Record<string, string | number>): string => {
    const own = c.t(key, vars)
    if (own !== key) return own
    const lang = (c.chat as { lang?: string } | undefined)?.lang ?? 'en'
    const raw = PACKS[lang]?.formguide?.[key] ?? FG_STRINGS[lang]?.[key] ?? FG_STRINGS.en[key]
    return raw ? raw.replace(/\{(\w+)\}/g, (m, n) => (vars && n in vars ? String(vars[n]) : m)) : key
  }
  return { ...c, t }
}

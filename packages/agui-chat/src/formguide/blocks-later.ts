/**
 * Cards from blocks without the blocks in the bundle: a card is drawn at once when the blocks are here (always with
 * a bundler; in the one-script build once agui-chat.blocks.js has arrived), otherwise its empty element is shown and
 * filled in place when the file arrives, so chat.updateCard, registerCard and a host's own renderer keep the element.
 */
import { h } from '../dom'
import { blocksNow, loadBlocks, type Blocks } from '#blocks-loader'
import type { Interrupt, RendererContext } from '../types'
import { blocksShell } from './blocks-base'
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
  return withBlocks(card, c, (b) => { b.blocksCard(it, c, answer, onAction, card) })
}

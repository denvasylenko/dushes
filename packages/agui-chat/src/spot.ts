/**
 * A card brought back (card_focus): the log scrolls to it, centred, and it glows for a moment (`data-spot`, styled by
 * the chat). Loaded with the tooltip and the menu (agui-chat.tip.js), the first time a card is asked for again.
 */
let glow: ReturnType<typeof setTimeout> | undefined

/** Scroll `log` (not the page) to `el` and ring it; `done` is called when the scroll has landed. */
export function spotCard(log: HTMLElement, el: HTMLElement, done: () => void): void {
  const top = el.getBoundingClientRect().top - log.getBoundingClientRect().top + log.scrollTop
  const target = Math.max(0, top - (log.clientHeight - el.offsetHeight) / 2)
  log.style.overflowAnchor = 'none'   // Chrome's scroll anchoring would cancel the smooth scroll as the text below types
  log.scrollTo?.({ top: target, behavior: globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
  // (no scrollend here: Chrome delivers a late one from the pin before this scroll; a timer ends it, and lands it)
  setTimeout(() => {
    log.style.overflowAnchor = ''
    if (Math.abs(log.scrollTop - target) > 4) log.scrollTop = target   // a smooth scroll something cut short
    done()
  }, 600)
  el.removeAttribute('data-spot'); void el.offsetWidth; el.setAttribute('data-spot', '')
  clearTimeout(glow)
  glow = setTimeout(() => el.removeAttribute('data-spot'), 1600)
}

// the one-script build: agui-chat.tip.js registers it on window.AguiChat
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.spotCard = spotCard

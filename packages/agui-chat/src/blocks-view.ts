/**
 * <agui-blocks>: cards drawn from blocks, outside a chat, with the chat's own look (its tokens, light and dark). For a
 * host's own panel next to the chat: a demo's "How it decided" tab, a summary page. Display only: nothing waits for an
 * answer; a button or a tap tells the page (`agui:block-action`).
 *
 *   import '@formguide/agui-chat/blocks-view'
 *   const view = document.querySelector('agui-blocks')
 *   view.cards = [{ id: 'turn-1', blocks: [{ type: 'title', text: 'Open car insurance' }, ...] }]
 *
 * Attributes: `scheme` (light, dark, or the system's), `lang`, `empty` (the line shown while there are no cards).
 * Not part of the one-script build: it is its own module, so the chat's main file does not grow.
 */
import { CSS } from './styles'
import { h } from './dom'
import { blocksCard } from './formguide/blocks'
import { FG_STRINGS } from './formguide/i18n'
import type { RendererContext } from './types'

export interface BlocksCard { id?: string; blocks: unknown[]; selected?: boolean }

const sheet = (): CSSStyleSheet | null => { try { const s = new CSSStyleSheet(); s.replaceSync(CSS); return s } catch { return null } }
let base: CSSStyleSheet | null | undefined

export class AguiBlocksElement extends HTMLElement {
  static observedAttributes = ['scheme', 'lang', 'empty']
  private _cards: BlocksCard[] = []
  private _list: HTMLElement
  private _media = typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: dark)') : null

  constructor() {
    super()
    const root = this.attachShadow({ mode: 'open' })
    base ??= sheet()
    if (base) root.adoptedStyleSheets = [base]; else root.append(h('style', null, CSS))
    this._list = h('div', { class: 'log bv', part: 'list', role: 'list' })
    root.append(h('style', null, ':host { display: block; } .bv { overflow: visible; padding: 0; } .bv > .card { margin: 0 0 12px; } .bv > .card[aria-current=true] { box-shadow: 0 0 0 2px var(--agui-ink); } .bv > .bv-empty { padding: 48px 24px; text-align: center; } .bv .card-q { font-size: 15px; margin-bottom: 2px; }'), this._list)
  }

  connectedCallback(): void { this._media?.addEventListener('change', this._scheme); this._scheme(); this._draw() }
  disconnectedCallback(): void { this._media?.removeEventListener('change', this._scheme) }
  attributeChangedCallback(): void { this._scheme(); this._draw() }

  /** The cards, oldest first or newest first, as the page wants them shown. */
  get cards(): BlocksCard[] { return this._cards }
  set cards(v: BlocksCard[]) { this._cards = Array.isArray(v) ? v : []; this._draw() }

  private _scheme = (): void => {
    const s = this.getAttribute('scheme')
    this.classList.toggle('dark', s === 'dark' || (s !== 'light' && !!this._media?.matches))
  }

  private _ctx(): RendererContext {
    const lang = this.getAttribute('lang') || document.documentElement.lang || 'en'
    const t = (key: string, vars?: Record<string, string | number>): string =>
      (FG_STRINGS[lang]?.[key] ?? FG_STRINGS.en[key] ?? key).replace(/\{(\w+)\}/g, (_, n: string) => String(vars?.[n] ?? ''))
    const tell = (id: string, label: string): void => { this.dispatchEvent(new CustomEvent('agui:block-action', { bubbles: true, composed: true, detail: { id, label } })) }
    return { resolve: () => {}, t, flags: {}, restored: true,
      chat: { lang, send: (text: string) => tell('', text) } as unknown as RendererContext['chat'] }
  }

  private _draw(): void {
    if (!this.isConnected) return
    const c = this._ctx()
    if (!this._cards.length) {
      const empty = this.getAttribute('empty')
      this._list.replaceChildren(...(empty ? [h('div', { class: 'muted bv-empty' }, empty)] : []))
      return
    }
    this._list.replaceChildren(...this._cards.map((it) => {
      const body = blocksCard({ blocks: it.blocks }, c, null, async (id, label) => {
        this.dispatchEvent(new CustomEvent('agui:block-action', { bubbles: true, composed: true, detail: { id, label, card: it.id } }))
        return true
      })
      return h('div', { class: 'card', part: 'card', role: 'listitem', 'data-card-id': it.id ?? null, 'aria-current': it.selected ? 'true' : null }, body)
    }))
  }
}

if (typeof customElements !== 'undefined' && !customElements.get('agui-blocks')) customElements.define('agui-blocks', AguiBlocksElement)

declare global {
  interface HTMLElementTagNameMap { 'agui-blocks': AguiBlocksElement }
}

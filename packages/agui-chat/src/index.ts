/**
 * @formguide/agui-chat: an AG-UI chat as a Web Component.
 *
 *   import '@formguide/agui-chat'                 // defines <agui-chat>
 *   import { formguide } from '@formguide/agui-chat/formguide'
 *   document.querySelector('agui-chat').use(formguide({ getState, applyChanges }))
 */
import { AguiChatElement } from './element'

export { AguiChatElement, DEFAULTS } from './element'
export { h, md, esc } from './dom'
export { sseEvents, runHttp, runAgent, uid } from './transport'
export { shrinkImage } from './image'
export { keyLabel, ariaKeys, isMac } from './keys'
export type { TipRow } from './tip'
export { defineTheme, themes, themeCss, TOKENS, THEME_PACKS, loadTheme } from './themes'
export { addLanguage, loadLanguage, LANGUAGES } from './langs'
export type { LangPack } from './langs'
export type { Theme, Tokens } from './themes'
export type * from './types'

/** Define the element (done on import; call again to use another tag name). */
export function define(tag = 'agui-chat'): void {
  if (typeof customElements !== 'undefined' && !customElements.get(tag)) {
    customElements.define(tag, tag === 'agui-chat' ? AguiChatElement : class extends AguiChatElement {})
  }
}

define()

declare global {
  interface HTMLElementTagNameMap { 'agui-chat': AguiChatElement }
}

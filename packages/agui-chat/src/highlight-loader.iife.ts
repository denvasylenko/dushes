/** The field highlight for the one-script build: agui-chat.highlight.js next to agui-chat.iife.js registers itself. */
import type * as H from './highlight'
import { loadFile } from './lang-loader.iife'

export const loadHighlight = (): Promise<Pick<typeof H, 'highlightField' | 'lookAt'>> => loadFile('agui-chat.highlight.js')
  .then(() => (globalThis as unknown as { AguiChat: Pick<typeof H, 'highlightField' | 'lookAt'> }).AguiChat)

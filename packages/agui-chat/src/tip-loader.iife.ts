/** The shortcut tooltip for the one-script build: agui-chat.tip.js next to agui-chat.iife.js registers itself. */
import type { attachTip } from './tip'
import { loadFile } from './lang-loader.iife'

export const loadTip = (): Promise<typeof attachTip> => loadFile('agui-chat.tip.js')
  .then(() => (globalThis as unknown as { AguiChat: { attachTip: typeof attachTip } }).AguiChat.attachTip)

/** The card blocks for the one-script build: agui-chat.blocks.js next to agui-chat.iife.js, added the first time
 *  a card from blocks is shown (or a run starts), so the chat itself stays small. */
import type { Blocks } from './blocks-loader'
import { loadFile } from './lang-loader.iife'

let ready: Blocks | null = null
let loading: Promise<Blocks> | null = null

export const blocksNow = (): Blocks | null => ready

export const loadBlocks = (): Promise<Blocks> => (loading ??= loadFile('agui-chat.blocks.js').then(() => {
  const b = (globalThis as unknown as { AguiChat?: { blocks?: Blocks } }).AguiChat?.blocks
  if (!b) throw new Error('agui-chat: agui-chat.blocks.js did not register')
  return (ready = b)
}).catch((e) => { loading = null; throw e }))   // a later card tries again

/** The shortcut tooltip for the one-script build: agui-chat.tip.js next to agui-chat.iife.js registers itself. */
import type { attachTip } from './tip'
import { loadFile } from './lang-loader.iife'

// loaded once: a second script would be a second copy of the menu, which could not close the first one's
let file: Promise<null> | undefined
const tip = (): Promise<null> => (file ??= loadFile('agui-chat.tip.js'))

export const loadTip = (): Promise<typeof attachTip> => tip()
  .then(() => (globalThis as unknown as { AguiChat: { attachTip: typeof attachTip } }).AguiChat.attachTip)

import type { openMenu } from './menu'
/** The + menu: in agui-chat.tip.js too. */
export const loadMenu = (): Promise<typeof openMenu> => tip()
  .then(() => (globalThis as unknown as { AguiChat: { openMenu: typeof openMenu } }).AguiChat.openMenu)

import type { spotCard } from './spot'
/** Bringing a card back (card_focus): in agui-chat.tip.js too. */
export const loadSpot = (): Promise<typeof spotCard> => tip().then(() => (globalThis as unknown as { AguiChat: { spotCard: typeof spotCard } }).AguiChat.spotCard)

import type { fillSources } from './sources'
/** The source links and their sheet: in agui-chat.tip.js too. */
export const loadSources = (): Promise<typeof fillSources> => tip().then(() => (globalThis as unknown as { AguiChat: { fillSources: typeof fillSources } }).AguiChat.fillSources)

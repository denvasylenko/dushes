/** The shortcut tooltip for ES module builds: its own chunk, loaded on the first hover or focus of a button. */
import type { attachTip } from './tip'

export const loadTip = (): Promise<typeof attachTip> => import('./tip').then((m) => m.attachTip)

import type { openMenu } from './menu'
/** The + menu: the same chunk as the tooltip. */
export const loadMenu = (): Promise<typeof openMenu> => import('./tip').then((m) => m.openMenu)

import type { spotCard } from './spot'
/** Bringing a card back (card_focus): the same chunk. */
export const loadSpot = (): Promise<typeof spotCard> => import('./tip').then((m) => m.spotCard)

import type { fillSources } from './sources'
/** The source links under an answer and the sheet a tap opens: the same chunk. */
export const loadSources = (): Promise<typeof fillSources> => import('./tip').then((m) => m.fillSources)

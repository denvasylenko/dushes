/** The shortcut tooltip for ES module builds: its own chunk, loaded on the first hover or focus of a button. */
import type { attachTip } from './tip'

export const loadTip = (): Promise<typeof attachTip> => import('./tip').then((m) => m.attachTip)

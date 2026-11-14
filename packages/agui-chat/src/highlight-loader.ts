/** The field highlight for ES module builds: its own chunk, loaded the first time a field is highlighted. */
import type * as H from './highlight'

export const loadHighlight = (): Promise<typeof H> => import('./highlight')

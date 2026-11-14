/** The card blocks for ES module builds: part of the formguide entry (blocksCard is public and synchronous there),
 *  so they are always ready. The one-script build swaps in blocks-loader.iife.ts. */
import { blocksCard, blocksRenderer } from './formguide/blocks'
import { monthCalendar } from './formguide/month'
import { realTypedView } from './formguide/typed'

export interface Blocks { blocksCard: typeof blocksCard; blocksRenderer: typeof blocksRenderer; calendar: typeof monthCalendar; typedView: typeof realTypedView }

const blocks: Blocks = { blocksCard, blocksRenderer, calendar: monthCalendar, typedView: realTypedView }
/** The blocks when they are here already (always, in this build). */
export const blocksNow = (): Blocks | null => blocks
export const loadBlocks = (): Promise<Blocks> => Promise.resolve(blocks)

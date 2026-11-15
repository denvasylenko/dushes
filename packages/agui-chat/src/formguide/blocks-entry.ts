/** The card blocks as their own script for the one-script build: agui-chat.blocks.js registers them on
 *  window.AguiChat (it loads after agui-chat.iife.js, when the first card from blocks is shown). */
import { blocksCard, blocksRenderer, styled } from './blocks'
import type { Blocks } from '../blocks-loader'
import { monthCalendar } from './month'   // the date picker's month grid travels with the blocks
import { realTypedView } from './typed'   // so do a question's typed answers (days, slots, a range, an address)
import { realReviewCard } from './review'   // and the review card

const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
const blocks: Blocks = { blocksCard, blocksRenderer, calendar: (...a) => styled(monthCalendar(...a)), typedView: (...a) => styled(realTypedView(...a)), reviewCard: (...a) => styled(realReviewCard(...a)) }
if (g.AguiChat) g.AguiChat.blocks = blocks

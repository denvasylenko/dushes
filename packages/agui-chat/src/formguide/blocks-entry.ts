/** The card blocks as their own script for the one-script build: agui-chat.blocks.js registers them on
 *  window.AguiChat (it loads after agui-chat.iife.js, when the first card from blocks is shown). */
import { blocksCard, blocksRenderer } from './blocks'
import { monthCalendar } from './month'   // the date picker's month grid travels with the blocks
import { realTypedView } from './typed'   // so do a question's typed answers (days, slots, a range, an address)

const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.blocks = { blocksCard, blocksRenderer, calendar: monthCalendar, typedView: realTypedView }

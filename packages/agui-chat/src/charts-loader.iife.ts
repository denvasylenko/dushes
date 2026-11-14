/** Chart.js for the one-script build: agui-chat.charts.js next to agui-chat.iife.js registers AguiChat.drawChart. */
import type { DrawChart } from './formguide/chart'
import { loadFile } from './lang-loader.iife'

let loading: Promise<DrawChart> | null = null
export const loadCharts = (): Promise<DrawChart> => (loading ??= loadFile('agui-chat.charts.js').then(() => {
  const draw = (globalThis as unknown as { AguiChat?: { drawChart?: DrawChart } }).AguiChat?.drawChart
  if (!draw) throw new Error('agui-chat: agui-chat.charts.js did not register')
  return draw
}).catch((e) => { loading = null; throw e }))   // a later chart tries again

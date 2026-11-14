/** Chart.js for ES module builds: its own chunk, loaded the first time a column, line or area chart shows. */
import type { DrawChart } from './formguide/chart'

export const loadCharts = (): Promise<DrawChart> => import('./formguide/chart-draw').then((m) => m.drawChart)

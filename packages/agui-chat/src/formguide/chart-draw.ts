/**
 * Columns, a line and an area on a canvas with Chart.js (MIT, https://www.chartjs.org), in the chat's look: one
 * accent, quiet axes (a baseline, a few faint horizontal lines), 4 px rounded column tops, a 2 px line with its last
 * point marked, the theme's font. Loaded only when such a chart shows: its own chunk with a bundler,
 * agui-chat.charts.js next to the one-script build (it registers AguiChat.drawChart).
 */
import { BarController, BarElement, CategoryScale, Chart, Filler, LinearScale, LineController, LineElement, PointElement, Tooltip } from 'chart.js'
import type { ChartLook, ChartSpec } from './chart'

Chart.register(BarController, BarElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip)

const alpha = (rgba: string, a: number): string => rgba.replace(/rgba?\(([^,]+),([^,]+),([^,)]+)(?:,[^)]*)?\)/, `rgba($1,$2,$3, ${a})`)

export function drawChart(canvas: HTMLCanvasElement, spec: ChartSpec, look: ChartLook): () => void {
  const bar = spec.kind === 'bar'
  const many = spec.series.length > 1
  const font = { family: look.font, size: 11 }
  const chart = new Chart(canvas, {
    type: bar ? 'bar' : 'line',
    data: {
      labels: spec.labels,
      datasets: spec.series.map((s, i) => {
        const color = look.colors[i] ?? look.colors[0]
        const last = s.data.length - 1
        return bar ? {
          label: s.name, data: s.data, borderWidth: 0, borderRadius: 4, borderSkipped: 'start' as const, maxBarThickness: 24,
          categoryPercentage: many ? 0.7 : 0.8, barPercentage: many ? 0.9 : 0.85,
          // one bar is the point: it keeps the colour, the others go grey
          backgroundColor: spec.highlight ? spec.labels.map((l) => (l === spec.highlight ? color : alpha(look.muted, 0.35))) : color,
          hoverBackgroundColor: color,
        } : {
          label: s.name, data: s.data, borderColor: color, borderWidth: 2, borderCapStyle: 'round' as const, borderJoinStyle: 'round' as const,
          cubicInterpolationMode: 'monotone' as const, fill: spec.kind === 'area' && !many ? 'origin' : false,
          backgroundColor: alpha(color, 0.1),
          pointRadius: s.data.map((_, k) => (k === last ? 4 : 0)), pointHoverRadius: 5,
          pointBackgroundColor: color, pointBorderColor: look.surface, pointBorderWidth: 2, pointHitRadius: 12,
        }
      }),
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: look.reduced ? false : { duration: 400, easing: 'easeOutCubic' },
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 6, right: 4 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: look.surface, titleColor: look.muted, bodyColor: look.ink, borderColor: look.grid, borderWidth: 1,
          padding: 8, cornerRadius: 8, displayColors: many, boxWidth: 8, boxHeight: 8, usePointStyle: false,
          titleFont: font, bodyFont: { ...font, size: 13, weight: 600 },
          callbacks: { label: (ctx) => `${many ? `${ctx.dataset.label}: ` : ''}${look.format(Number(ctx.parsed.y))}` },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { color: look.grid }, ticks: { color: look.muted, font, maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } },
        y: {
          beginAtZero: bar || spec.kind === 'area', grid: { color: look.grid }, border: { display: false },
          ticks: { color: look.muted, font, maxTicksLimit: 4, padding: 6,
            callback: (v, _i, ticks) => {
              const step = ticks.length > 1 ? Math.abs(ticks[1].value - ticks[0].value) : 1
              return look.format(Number(v), step >= 1 ? 0 : Math.min(2, Math.ceil(-Math.log10(step) - 1e-9)))
            } },
        },
      },
    },
  })
  return () => chart.destroy()
}

// the one-script build: register on window.AguiChat (agui-chat.charts.js loads after agui-chat.iife.js)
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.drawChart = drawChart

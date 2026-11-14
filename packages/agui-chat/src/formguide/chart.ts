/**
 * Charts in cards, from the theme's tokens: columns (`bar`), a `line`, an `area`, a `barList` (a ranking), a
 * `stacked` bar (parts of a whole) and a `meter` (a value against a limit).
 *
 *   { type: 'chart', kind: 'bar', title: 'Visits by day', unit: '', data: [{ label: 'Mon', value: 12 }, ...] }
 *   { type: 'chart', kind: 'line', labels: ['Jun', 'Jul', ...], series: [{ name: 'Rate', data: [18.2, 18.9, ...] }], unit: '%' }
 *   { type: 'chart', kind: 'meter', label: 'Debt to income', value: 38, max: 100, limit: 50, unit: '%' }
 *
 * The bar list, the stacked bar and the meter are plain HTML. Columns, line and area are drawn by Chart.js (MIT),
 * which loads the first time such a chart shows (its own chunk; agui-chat.charts.js next to the one-script build).
 * Every chart has a text summary for screen readers and its numbers in a table under "Show data".
 */
import { h } from '../dom'
import { loadCharts } from '#charts-loader'
import type { RendererContext } from '../types'

export interface Series { name: string; data: number[] }
export interface ChartSpec { kind: 'bar' | 'line' | 'area'; labels: string[]; series: Series[]; highlight?: string }
/** What a chart looks like, read from the chat's tokens when it is drawn (so a theme or dark mode follows). */
export interface ChartLook {
  colors: string[]; ink: string; muted: string; grid: string; surface: string; font: string
  reduced: boolean; format: (v: number, digits?: number) => string
}
export type DrawChart = (canvas: HTMLCanvasElement, spec: ChartSpec, look: ChartLook) => () => void

type Item = Record<string, unknown>
const str = (v: unknown): string => (v == null ? '' : String(v))
const num = (v: unknown): number | null => { const n = typeof v === 'number' ? v : Number(v); return Number.isFinite(n) ? n : null }
const MAX_POINTS = 60
const MAX_SERIES = 8
// the categorical order after the theme's accent: fixed, never cycled (a 9th series is left out)
const SERIES = ['#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']

/** Labels and series from `data: [{label, value}]`, `data: [1, 2]` with `labels`, or `series: [{name, data}]`. */
export function chartData(b: Item): { labels: string[]; series: Series[] } {
  if (Array.isArray(b.series)) {
    const series = (b.series as Item[]).filter((s) => s && typeof s === 'object').slice(0, MAX_SERIES)
      .map((s) => ({ name: str(s.name), data: (Array.isArray(s.data) ? s.data : []).slice(0, MAX_POINTS).map((v) => num(v) ?? 0) }))
    const n = Math.max(0, ...series.map((s) => s.data.length))
    const labels = (Array.isArray(b.labels) ? b.labels.map(str) : []).slice(0, n)
    while (labels.length < n) labels.push(String(labels.length + 1))
    return { labels, series }
  }
  const raw = (Array.isArray(b.data) ? b.data : []).slice(0, MAX_POINTS)
  const given = Array.isArray(b.labels) ? b.labels.map(str) : []
  const labels: string[] = [], data: number[] = []
  raw.forEach((x, i) => {
    if (x && typeof x === 'object') { labels.push(str((x as Item).label)); data.push(num((x as Item).value) ?? 0) }
    else { labels.push(given[i] ?? String(i + 1)); data.push(num(x) ?? 0) }
  })
  return { labels, series: data.length ? [{ name: str(b.title), data }] : [] }
}

/** "1 240 €", "18,9%": the chat's language, the unit after the number ("%" without a space). */
export function formatter(lang: string, unit: unknown): (v: number, digits?: number) => string {
  const nf = (o: Intl.NumberFormatOptions): Intl.NumberFormat => { try { return new Intl.NumberFormat(lang || 'en', o) } catch { return new Intl.NumberFormat('en', o) } }
  const plain = nf({ maximumFractionDigits: 2 })
  const fixed = [0, 1, 2].map((d) => nf({ minimumFractionDigits: d, maximumFractionDigits: d }))
  const u = str(unit)
  // digits: an axis shows every tick with its step's precision (17.5, 18.0, 18.5), never "18" twice
  return (v, digits) => `${(digits == null ? plain : fixed[Math.max(0, Math.min(2, digits))]).format(v)}${u ? (u === '%' ? '%' : `\u00a0${u}`) : ''}`
}

/** A CSS colour (a token, color-mix, a name) as rgb(...) the canvas understands. */
function rgb(color: string, alpha = 1): string {
  const probe = h('span', { style: `color: ${color}; display: none` })
  document.body.append(probe)
  const c = getComputedStyle(probe).color || color
  probe.remove()
  const m = c.match(/rgba?\(([^)]+)\)/)
  if (!m) return color
  const [r, g, b] = m[1].split(/[ ,/]+/).filter(Boolean)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function look(c: RendererContext, unit: unknown): ChartLook {
  const host = c.chat.host
  const css = getComputedStyle(host)
  const tok = (name: string, fallback: string): string => css.getPropertyValue(name).trim() || fallback
  const accent = rgb(tok('--agui-link', '#0a84ff'))
  return {
    colors: [accent, ...SERIES.map((x, i) => rgb(tok(`--agui-series-${i + 2}`, x)))],
    ink: rgb(tok('--agui-ink', '#1d1d1f')), /* axis labels are text: ink-2 */ muted: rgb(tok('--agui-ink-2', '#6e6e73')),
    grid: rgb(tok('--agui-line', 'rgba(0,0,0,.08)')), surface: rgb(tok('--agui-panel-bg', tok('--agui-bg', '#ffffff'))),
    font: tok('--agui-font', '-apple-system, BlinkMacSystemFont, sans-serif'),
    reduced: !!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
    format: formatter(c.chat.lang, unit),
  }
}

/** The numbers as a table, under "Show data": the chart's text form. */
function table(labels: string[], series: Series[], f: (v: number) => string, c: RendererContext): HTMLElement {
  return h('details', { class: 'bk-data' }, h('summary', null, c.t('showData')),
    h('table', null,
      series.length > 1 ? h('tr', null, h('th', null, ''), series.map((s) => h('th', null, s.name))) : null,
      labels.map((l, i) => h('tr', null, h('th', { scope: 'row' }, l), series.map((s) => h('td', null, f(s.data[i] ?? 0)))))))
}

const head = (b: Item): HTMLElement | null => (b.title || b.subtitle
  ? h('div', { class: 'bk-chart-t' }, b.title ? h('div', { class: 'bk-strong' }, str(b.title)) : null, b.subtitle ? h('div', { class: 'muted bk-small' }, str(b.subtitle)) : null)
  : null)

/** The `chart` block. */
export function chartBlock(b: Item, c: RendererContext): HTMLElement {
  const kind = str(b.kind) || 'bar'
  const f = formatter(c.chat.lang, b.unit)
  const box = h('div', { class: `bk-chart bk-chart-${kind}`, part: 'block-chart' }, head(b))

  if (kind === 'meter') {   // a value against a limit: one track, the value and the limit under it
    const max = num(b.max) ?? 100, value = num(b.value) ?? 0, limit = num(b.limit)
    const pct = Math.max(0, Math.min(100, (value / (max || 1)) * 100))
    const over = limit != null && value > limit
    box.append(
      h('div', { class: `bk-meter${over ? ' over' : ''}`, role: 'meter', 'aria-valuenow': String(value), 'aria-valuemin': '0', 'aria-valuemax': String(max),
        'aria-label': str(b.label || b.title) }, h('i', { style: `width: ${pct}%` }),
        limit != null ? h('b', { style: `left: ${Math.max(0, Math.min(100, (limit / (max || 1)) * 100))}%`, 'aria-hidden': 'true' }) : null),
      h('div', { class: 'bk-meter-l' }, h('span', null, b.label ? `${str(b.label)} · ${f(value)}` : f(value)),
        limit != null ? h('span', { class: 'muted' }, `${c.t('limit')} ${f(limit)}`) : null))
    return box
  }

  const { labels, series } = chartData(b)
  if (!series.length || !labels.length) { box.append(h('div', { class: 'muted bk-small bk-empty' }, str(b.empty) || c.t('noData'))); return box }
  // HTML parts take the colours as CSS (they follow a theme or dark mode by themselves); the canvas reads them when drawn
  const colors = ['var(--agui-link)', ...SERIES.map((x, i) => `var(--agui-series-${i + 2}, ${x})`)]

  if (kind === 'barList') {   // a ranking with long names: rows, each a label, its number and a bar
    const data = series[0].data
    const max = Math.max(...data.map(Math.abs), 1)
    box.append(h('div', { class: 'bk-barlist' }, labels.map((l, i) => h('div', { class: 'bk-bl' },
      h('div', { class: 'bk-bl-t' }, h('span', null, l), h('span', { class: 'bk-num' }, f(data[i]))),
      h('div', { class: 'bk-track' }, h('i', { style: `width: ${(Math.abs(data[i]) / max) * 100}%` }))))))
    return box
  }

  if (kind === 'stacked') {   // parts of a whole: one bar of segments, a legend with each part's share
    const data = series[0].data.map((v) => Math.max(0, v))
    const sum = data.reduce((a, x) => a + x, 0) || 1
    box.append(
      h('div', { class: 'bk-stack', role: 'img', 'aria-label': labels.map((l, i) => `${l} ${Math.round((data[i] / sum) * 100)}%`).join(', ') },
        data.map((v, i) => h('i', { style: `flex: ${v} 1 0; background: ${colors[i % colors.length]}` }))),
      h('div', { class: 'bk-legend' }, labels.map((l, i) => h('span', null, h('i', { style: `background: ${colors[i % colors.length]}` }),
        `${l} ${Math.round((data[i] / sum) * 100)}%`))))
    return box
  }

  // columns, line, area: Chart.js on a canvas, its room kept while it loads
  const spec: ChartSpec = { kind: kind === 'line' || kind === 'area' ? kind : 'bar', labels, series, highlight: b.highlight ? str(b.highlight) : undefined }
  const last = series.map((s) => `${series.length > 1 && s.name ? `${s.name} ` : ''}${f(s.data[s.data.length - 1] ?? 0)}`).join(', ')
  const canvas = h('canvas', { role: 'img', 'aria-label': `${str(b.title) || spec.kind}: ${labels[0]}–${labels[labels.length - 1]}, ${c.t('latest')} ${last}` }) as HTMLCanvasElement
  const height = Math.max(120, Math.min(320, num(b.height) ?? 180))
  const stage = h('div', { class: 'bk-canvas', style: `height: ${height}px` }, canvas)
  box.append(stage)
  if (series.length > 1) {
    box.append(h('div', { class: 'bk-legend' }, series.map((s, i) => h('span', null, h('i', { style: `background: ${colors[i]}` }), s.name))))
  }
  box.append(table(labels, series, f, c))
  let destroy: (() => void) | null = null
  const draw = (): void => {
    void loadCharts().then((fn) => {
      destroy?.()
      destroy = fn(canvas, spec, look(c, b.unit))
    }, () => { stage.remove(); box.querySelector('details')?.setAttribute('open', '') })   // no chart file: the numbers stay
  }
  draw()
  // light <-> dark: drawn again with the new tokens
  const mq = globalThis.matchMedia?.('(prefers-color-scheme: dark)')
  mq?.addEventListener?.('change', () => { if (box.isConnected) draw() })
  return box
}

/** A sparkline for the `stat` block (`spark: [numbers]`): a thin line and a faint area, no axes. */
export function sparkline(values: unknown): SVGSVGElement | null {
  const v = (Array.isArray(values) ? values : []).map(num).filter((x): x is number => x != null).slice(-MAX_POINTS)
  if (v.length < 2) return null
  const min = Math.min(...v), max = Math.max(...v), span = max - min || 1
  const pts = v.map((y, i) => `${((i / (v.length - 1)) * 200).toFixed(1)},${(36 - ((y - min) / span) * 32).toFixed(1)}`)
  const ns = 'http://www.w3.org/2000/svg'
  const svg = document.createElementNS(ns, 'svg')
  svg.setAttribute('viewBox', '0 0 200 40'); svg.setAttribute('preserveAspectRatio', 'none'); svg.setAttribute('class', 'bk-spark'); svg.setAttribute('aria-hidden', 'true')
  const area = document.createElementNS(ns, 'polygon'); area.setAttribute('points', `0,40 ${pts.join(' ')} 200,40`); area.setAttribute('class', 'a')
  const line = document.createElementNS(ns, 'polyline'); line.setAttribute('points', pts.join(' ')); line.setAttribute('class', 'l')
  svg.append(area, line)
  return svg
}

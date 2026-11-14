import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { formguide } from '../src/formguide/index'
import { chartData, formatter } from '../src/formguide/chart'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
async function mount(): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
  el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
  document.body.appendChild(el)
  await tick()
  return el
}
const show = async (el: AguiChatElement, blocks: Record<string, unknown>[]) => { void el.showCard({ type: 'blocks', blocks }); await tick(20) }
const $ = (el: AguiChatElement, s: string) => el.shadowRoot!.querySelector(s) as HTMLElement
const $$ = (el: AguiChatElement, s: string) => [...el.shadowRoot!.querySelectorAll(s)] as HTMLElement[]

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('chart data', () => {
  it('takes [{label, value}], numbers with labels, or series; cuts at 8 series', () => {
    expect(chartData({ data: [{ label: 'Mon', value: 3 }, { label: 'Tue', value: '5' }] })).toEqual({ labels: ['Mon', 'Tue'], series: [{ name: '', data: [3, 5] }] })
    expect(chartData({ data: [1, 2], labels: ['a'] }).labels).toEqual(['a', '2'])
    const many = chartData({ labels: ['x'], series: Array.from({ length: 10 }, (_, i) => ({ name: `s${i}`, data: [i] })) })
    expect(many.series).toHaveLength(8)
  })

  it('formats in the chat language with the unit after the number', () => {
    expect(formatter('en', '€')(1240)).toBe('1,240 €')
    expect(formatter('en', '%')(18.9)).toBe('18.9%')
    expect(formatter('de', '')(1240.5)).toBe('1.240,5')
  })
})

describe('chart blocks', () => {
  it('columns: a canvas with a summary, the numbers under "Show data", no legend for one series', async () => {
    const el = await mount()
    await show(el, [{ type: 'chart', kind: 'bar', title: 'Visits by day', data: [{ label: 'Mon', value: 12 }, { label: 'Tue', value: 30 }] }])
    expect($(el, '.bk-chart-bar .bk-strong').textContent).toBe('Visits by day')
    expect($(el, '.bk-chart canvas').getAttribute('aria-label')).toBe('Visits by day: Mon–Tue, latest 30')
    expect($$(el, '.bk-data tr').map((r) => r.textContent)).toEqual(['Mon12', 'Tue30'])
    expect($(el, '.bk-chart .bk-legend')).toBeNull()
  })

  it('a line of two series has a legend', async () => {
    const el = await mount()
    await show(el, [{ type: 'chart', kind: 'line', labels: ['Jun', 'Jul'], unit: '%', series: [{ name: 'Car', data: [18, 19] }, { name: 'Home', data: [9, 9.5] }] }])
    expect($$(el, '.bk-legend span').map((s) => s.textContent)).toEqual(['Car', 'Home'])
    expect($$(el, '.bk-data th').map((t) => t.textContent)).toContain('Home')
  })

  it('a bar list, a stacked bar and a meter are plain HTML', async () => {
    const el = await mount()
    await show(el, [
      { type: 'chart', kind: 'barList', data: [{ label: 'Haircut', value: 48 }, { label: 'Beard', value: 24 }] },
      { type: 'chart', kind: 'stacked', unit: '€', data: [{ label: 'Principal', value: 62 }, { label: 'Interest', value: 30 }, { label: 'Insurance', value: 8 }] },
      { type: 'chart', kind: 'meter', label: 'Debt to income', value: 55, max: 100, limit: 50, unit: '%' },
    ])
    expect($$(el, '.bk-track > i').map((i) => i.style.width)).toEqual(['100%', '50%'])
    expect($$(el, '.bk-chart-stacked .bk-legend span').map((s) => s.textContent)).toEqual(['Principal 62%', 'Interest 30%', 'Insurance 8%'])
    const meter = $(el, '.bk-meter')
    expect(meter.classList.contains('over')).toBe(true)                // over the limit: shown in red
    expect(meter.querySelector('b')!.style.left).toBe('50%')            // the limit's mark
    expect($(el, '.bk-meter-l').textContent).toBe('Debt to income · 55%limit 50%')
  })

  it('no data: says so instead of empty axes; a stat shows its change and a sparkline', async () => {
    const el = await mount()
    await show(el, [{ type: 'chart', kind: 'bar', data: [] }, { type: 'stat', value: '1 240 €', label: 'This month', change: '+12%', spark: [3, 5, 4, 8] }])
    expect($(el, '.bk-empty').textContent).toBe('No data for this period')
    expect($(el, '.bk-change').classList.contains('tone-ok')).toBe(true)
    expect($(el, '.bk-spark polyline')).not.toBeNull()
  })
})

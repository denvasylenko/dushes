/**
 * The demo form: a small loan application rendered with plain DOM and bridged to formguide with the
 * same `schemaForm` a real integration uses, so cards, action chips and Undo go through real code.
 */
import { schemaForm, type FormSchema, type FormState, type Directive } from '../../../packages/agui-chat/src/formguide/index'
import { buildSelect } from '../components/ui/ui'
import { highlightField } from '../../../packages/agui-chat/src/highlight'

type Values = Record<string, unknown>

export const LOAN_TYPES = [
  { id: 'auto', name: 'Car loan' },
  { id: 'personal', name: 'Personal loan' },
  { id: 'mortgage', name: 'Mortgage' },
]
export const TERMS = ['12', '24', '36', '48', '60'].map((m) => ({ id: m, name: `${m} months` }))
export const EMPLOYMENT = [
  { id: 'employed', name: 'Employed' },
  { id: 'self', name: 'Self-employed' },
  { id: 'retired', name: 'Retired' },
]
/** Fields in dollars: a "$" sits inside the field, before the number (the label stays clean, as in Apple's forms). */
const UNITS: Record<string, string> = { monthly_income: '$', amount: '$' }
const MAKES = ['Toyota', 'Honda', 'Tesla', 'Ford'].map((m) => ({ id: m.toLowerCase(), name: m }))

export const SCHEMA: FormSchema = {
  id: 'landing_loan',   // the live demo's form on dushes-ai (backend/demo/landing/landing_loan.jsx)
  title: 'Loan application',
  sections: [
    {
      name: 'applicant', label: 'Applicant', fields: [
        { name: 'full_name', label: 'Full name', required: true },
        { name: 'email', label: 'Email', required: true },
        { name: 'employment', label: 'Employment', type: 'radio', options: EMPLOYMENT },
        { name: 'monthly_income', label: 'Monthly income', type: 'number', help: 'After tax, in dollars' },
      ],
    },
    {
      name: 'loan', label: 'Loan', fields: [
        { name: 'loan_type', label: 'Loan type', type: 'select', options: LOAN_TYPES, required: true },
        { name: 'car_make', label: 'Car make', type: 'select', options: MAKES, visible: (v) => v.loan_type === 'auto' },
        { name: 'amount', label: 'Amount', type: 'number', help: 'In dollars' },
        { name: 'term', label: 'Term', type: 'radio', options: TERMS },
      ],
    },
  ],
}

const h = <K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, string> = {}, ...kids: (Node | string)[]) => {
  const el = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v)
  el.append(...kids)
  return el
}

export interface DemoForm {
  state: () => FormState
  values: () => Values
  apply: (changes: Record<string, unknown>) => Promise<FormState['config']>
  reveal: (d: Directive) => void
  reset: () => void
}

export function mountForm(root: HTMLElement): DemoForm {
  let values: Values = {}
  let tab = 'applicant'
  const bridge = schemaForm(SCHEMA, {
    getValues: () => values,
    setValue: (name, value) => { values = { ...values, [name]: value } },
  })

  const tabs = h('div', { class: 'df-tabs ui-tabs', role: 'tablist', 'aria-label': 'Sections' })
  const body = h('div', { class: 'df-body' })
  const progress = h('div', { class: 'df-progress' })
  root.replaceChildren(
    h('div', { class: 'df-head' }, h('div', { class: 'df-title' }, SCHEMA.title!), progress),
    tabs, body,
  )

  const fieldsOf = (s: string) => SCHEMA.sections.find((x) => x.name === s)!.fields

  function render(): void {
    const props = bridge.config().props as Record<string, Record<string, unknown>>
    // the sections as the design system's tabs (.ui-tab, ui.css); ← → move between them
    tabs.replaceChildren(...SCHEMA.sections.map((s, i, all) => {
      const on = s.name === tab
      const b = h('button', { type: 'button', role: 'tab', class: 'ui-tab', 'aria-selected': String(on), tabindex: on ? '0' : '-1' }, s.label!)
      b.addEventListener('click', () => { tab = s.name; render() })
      b.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
        e.preventDefault()
        tab = all[(i + (e.key === 'ArrowRight' ? 1 : -1) + all.length) % all.length].name
        render()
        tabs.querySelector<HTMLElement>('[aria-selected="true"]')?.focus()
      })
      return b
    }))
    body.replaceChildren(...fieldsOf(tab).filter((f) => props[f.name]?.visible !== false).map((f) => {
      const v = values[f.name]
      const id = `df-${f.name}`
      let input: HTMLElement
      if (f.type === 'radio') {
        // the design system's choice groups (ui.ts wires clicks and arrow keys): Term is a segmented control,
        // Employment a row of chips
        const seg = f.name === 'term'
        const opts = f.options as { id: string; name: string }[]
        const hit = opts.some((o) => o.id === v)
        input = h('div', { class: seg ? 'ui-seg' : 'ui-chips', role: 'radiogroup', 'aria-label': f.label!, 'data-ui-choice': f.name },
          ...opts.map((o, k) => h('button', { type: 'button', role: 'radio', class: seg ? '' : 'ui-chip', 'data-value': o.id,
            'aria-checked': String(v === o.id), tabindex: v === o.id || (!hit && k === 0) ? '0' : '-1' }, o.name.replace(' months', ' mo'))))
        input.addEventListener('ui-change', (e) => {
          values = { ...values, [f.name]: (e as CustomEvent<{ value: string }>).detail.value }
          render()
          root.querySelector<HTMLElement>(`[data-ui-choice="${f.name}"] [aria-checked="true"]`)?.focus()
        })
      } else if (f.type === 'select') {
        // the design system's Select (a pop-up menu; a sheet on a phone), not the browser's own
        input = buildSelect({
          id, label: f.label!, value: (v as string | null) ?? null, placeholder: 'Choose\u2026',
          options: (f.options as { id: string; name: string }[]).map((o) => ({ value: o.id, label: o.name })),
          onChange: (value) => { values = { ...values, [f.name]: value || null }; render(); document.getElementById(id)?.focus() },   // focus stays on the field after the redraw
        })
      } else {
        const inp = h('input', { id, class: 'df-in', type: f.type === 'number' ? 'text' : 'text', inputmode: f.type === 'number' ? 'numeric' : 'text', autocomplete: 'off', placeholder: (UNITS[f.name] ? f.help?.replace(/,? in dollars$/i, '').replace(/^In dollars$/i, '') : f.help) ?? '' }) as HTMLInputElement
        inp.value = v === null || v === undefined ? '' : f.type === 'number' ? Number(v).toLocaleString('en-US') : String(v)
        inp.addEventListener('change', () => {
          const raw = inp.value.trim()
          values = { ...values, [f.name]: raw === '' ? null : f.type === 'number' ? Number(raw.replace(/[^\d.]/g, '')) || null : raw }
          renderProgress()
        })
        // a currency sits inside the field, before the number (as in Apple's forms), not in the label
        const unit = UNITS[f.name]
        input = unit ? h('div', { class: 'df-affix' }, h('span', { class: 'df-unit', 'aria-hidden': 'true' }, unit), inp) : inp
        if (unit) inp.setAttribute('aria-label', `${f.label}, in ${unit === '$' ? 'dollars' : unit}`)
      }
      const label = f.type === 'radio' ? h('span', { class: 'df-label' }, f.label!) : h('label', { class: 'df-label', for: id }, f.label!)
      return h('div', { class: 'df-field', 'data-name': f.name }, label, input)
    }))
    renderProgress()
  }

  function renderProgress(): void {
    const all = SCHEMA.sections.flatMap((s) => s.fields).filter((f) => f.name !== 'car_make' || values.loan_type === 'auto')
    const done = all.filter((f) => values[f.name] !== undefined && values[f.name] !== null && values[f.name] !== '').length
    progress.textContent = `${done} of ${all.length} filled`
    progress.style.setProperty('--p', String(done / all.length))
  }

  /** The fields the chat filled: the widget's own highlight (@formguide/agui-chat/highlight), not a copy. */
  function flash(names: string[]): void {
    for (const n of names) highlightField(n, { root })
  }

  function scrollTo(el: HTMLElement): void {   // inside the form panel only: never move the page
    const box = body.getBoundingClientRect()
    const r = el.getBoundingClientRect()
    if (r.top < box.top || r.bottom > box.bottom) body.scrollTop += r.top - box.top - 12
  }

  render()
  return {
    state: () => ({ config: bridge.config(), jsx_hash: 'demo', form_id: SCHEMA.id, ui: { open_section: tab } }),
    values: () => values,
    async apply(changes) {
      const config = await bridge.apply(changes)
      const names = Object.keys(changes)
      const target = bridge.sectionOf(names[0])
      if (target && !fieldsOf(tab).some((f) => names.includes(f.name))) tab = target
      render()
      flash(names)
      return config
    },
    reveal(d) {
      const t = d.reveal?.find((r) => r.type === 'tab')
      tab = (t && 'tab' in t ? t.tab : bridge.sectionOf(d.target)) ?? tab
      render()
      const el = root.querySelector<HTMLElement>(`[data-name="${d.target}"]`)
      if (!el) return
      scrollTo(el)
      highlightField(el, { kind: 'look', hint: d.hint, scroll: false })   // the panel scrolled itself: the page stays
      if (matchMedia('(pointer: fine)').matches) el.querySelector<HTMLElement>('input, .ui-select-btn, button')?.focus({ preventScroll: true })   // no keyboard popping up on a phone
    },
    reset() { values = {}; tab = 'applicant'; render() },
  }
}

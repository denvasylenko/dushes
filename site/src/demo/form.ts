/**
 * The demo form: a small loan application rendered with plain DOM and bridged to formguide with the
 * same `schemaForm` a real integration uses, so cards, action chips and Undo go through real code.
 */
import { schemaForm, type FormSchema, type FormState, type Directive } from '../../../packages/agui-chat/src/formguide/index'

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
const MAKES = ['Toyota', 'Honda', 'Tesla', 'Ford'].map((m) => ({ id: m.toLowerCase(), name: m }))

export const SCHEMA: FormSchema = {
  id: 'loan_demo',
  title: 'Loan application',
  sections: [
    {
      name: 'applicant', label: 'Applicant', fields: [
        { name: 'full_name', label: 'Full name', required: true },
        { name: 'email', label: 'Email', required: true },
        { name: 'employment', label: 'Employment', type: 'radio', options: EMPLOYMENT },
        { name: 'monthly_income', label: 'Monthly income, $', type: 'number', help: 'After tax' },
      ],
    },
    {
      name: 'loan', label: 'Loan', fields: [
        { name: 'loan_type', label: 'Loan type', type: 'select', options: LOAN_TYPES, required: true },
        { name: 'car_make', label: 'Car make', type: 'select', options: MAKES, visible: (v) => v.loan_type === 'auto' },
        { name: 'amount', label: 'Amount, $', type: 'number' },
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

  const tabs = h('div', { class: 'df-tabs', role: 'tablist' })
  const body = h('div', { class: 'df-body' })
  const progress = h('div', { class: 'df-progress' })
  root.replaceChildren(
    h('div', { class: 'df-head' }, h('div', { class: 'df-title' }, SCHEMA.title!), progress),
    tabs, body,
  )

  const fieldsOf = (s: string) => SCHEMA.sections.find((x) => x.name === s)!.fields

  function render(): void {
    const props = bridge.config().props as Record<string, Record<string, unknown>>
    tabs.replaceChildren(...SCHEMA.sections.map((s) => {
      const b = h('button', { type: 'button', role: 'tab', class: 'df-tab', 'aria-selected': String(s.name === tab) }, s.label!)
      b.addEventListener('click', () => { tab = s.name; render() })
      return b
    }))
    body.replaceChildren(...fieldsOf(tab).filter((f) => props[f.name]?.visible !== false).map((f) => {
      const v = values[f.name]
      const id = `df-${f.name}`
      let input: HTMLElement
      if (f.type === 'radio') {
        input = h('div', { class: 'df-seg', role: 'radiogroup', 'aria-label': f.label! },
          ...(f.options as { id: string; name: string }[]).map((o) => {
            const b = h('button', { type: 'button', role: 'radio', 'aria-checked': String(v === o.id), class: 'df-segbtn' }, o.name.replace(' months', ' mo'))
            b.addEventListener('click', () => { values = { ...values, [f.name]: o.id }; render() })
            return b
          }))
      } else if (f.type === 'select') {
        const sel = h('select', { id, class: 'df-in' }, h('option', { value: '' }, 'Choose…'),
          ...(f.options as { id: string; name: string }[]).map((o) => {
            const opt = h('option', { value: o.id }, o.name)
            if (v === o.id) opt.setAttribute('selected', '')
            return opt
          }))
        sel.addEventListener('change', () => { values = { ...values, [f.name]: sel.value || null }; render() })
        input = sel
      } else {
        const inp = h('input', { id, class: 'df-in', type: f.type === 'number' ? 'text' : 'text', inputmode: f.type === 'number' ? 'numeric' : 'text', autocomplete: 'off', placeholder: f.help ?? '' }) as HTMLInputElement
        inp.value = v === null || v === undefined ? '' : f.type === 'number' ? Number(v).toLocaleString('en-US') : String(v)
        inp.addEventListener('change', () => {
          const raw = inp.value.trim()
          values = { ...values, [f.name]: raw === '' ? null : f.type === 'number' ? Number(raw.replace(/[^\d.]/g, '')) || null : raw }
          renderProgress()
        })
        input = inp
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

  function flash(names: string[]): void {
    for (const n of names) {
      const el = root.querySelector<HTMLElement>(`[data-name="${n}"]`)
      if (!el) continue
      el.classList.remove('df-flash')
      void el.offsetWidth
      el.classList.add('df-flash')
    }
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
      el.classList.remove('df-look')
      void el.offsetWidth
      el.classList.add('df-look')
      if (d.hint) el.dataset.hint = d.hint
      if (matchMedia('(pointer: fine)').matches) el.querySelector<HTMLElement>('input, select, button')?.focus({ preventScroll: true })   // no keyboard popping up on a phone
    },
    reset() { values = {}; tab = 'applicant'; render() },
  }
}

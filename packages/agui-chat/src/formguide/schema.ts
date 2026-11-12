/**
 * A bridge for forms that have no config of their own (react-hook-form, Formik, useState):
 * describe the form once, and get the JSX skeleton, a live config and an apply() for formguide.
 *
 *   const bridge = schemaForm(schema, {
 *     getValues: () => form.getValues(),
 *     setValue: (name, value) => form.setValue(name, value, { shouldDirty: true }),
 *     getErrors: () => ({ phone: 'Must be 10 digits' }),
 *   })
 *   bridge.jsx          // send once: POST /agent/layouts {jsx, form_id: schema.id, config: bridge.config()}
 *   bridge.config()     // {props, state} for every run
 *   bridge.apply({...}) // accepted card values -> the form -> the new config
 */
import type { FormState } from './index'

export type Values = Record<string, unknown>
export type Option = string | { id?: unknown; name?: unknown; value?: unknown; label?: unknown }
type Rule<T> = T | ((values: Values) => T)

export interface FieldSchema {
  name: string
  label?: string
  type?: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'radio' | 'multiselect' | 'bool'
  options?: Rule<Option[]>
  visible?: Rule<boolean>
  disabled?: Rule<boolean>
  required?: Rule<boolean>
  readonly?: boolean
  placeholder?: string
  /** A short note for the user and the agent, e.g. the expected format. */
  help?: string
  /** How the form stores a choice: the option's id (default), the whole option, or its name. */
  valueAs?: 'id' | 'option' | 'name'
}

export interface SectionSchema { name: string; label?: string; fields: FieldSchema[]; visible?: Rule<boolean> }

export interface FormSchema {
  /** The form id: picks the domain pack, the knowledge and the stored layout. */
  id: string
  title?: string
  sections: SectionSchema[]
  /** Show sections as tabs (default) or one after another. */
  layout?: 'tabs' | 'sections'
  /** An inline domain pack (persona, rules, starters...), sent with the layout. */
  domain?: Record<string, unknown>
}

export interface FormAccess {
  getValues: () => Values
  setValue: (name: string, value: unknown) => void | Promise<void>
  /** Field name -> message; nested library errors are flattened by the caller. */
  getErrors?: () => Record<string, string | undefined>
}

export interface SchemaBridge {
  jsx: string
  config: () => FormState['config']
  apply: (changes: Record<string, unknown>) => Promise<FormState['config']>
  /** The section a field is in (to open its tab before scrolling). */
  sectionOf: (field: string) => string | undefined
  fields: Map<string, FieldSchema>
}

const TAGS: Record<NonNullable<FieldSchema['type']>, string> = {
  text: 'Input', textarea: 'TextArea', number: 'NumberInput', date: 'DatePicker', select: 'Dropdown',
  radio: 'RadioGroup', multiselect: 'MultiSelect', bool: 'Checkbox',
}
const CHOICE = new Set(['select', 'radio', 'multiselect'])
const NAME = /^[A-Za-z_][\w.-]*$/

const rule = <T>(r: Rule<T> | undefined, values: Values, dflt: T): T =>
  r === undefined ? dflt : typeof r === 'function' ? (r as (v: Values) => T)(values) : r

/** Any option shape -> {id, name}. */
export function normOption(o: Option): { id: string; name: string } {
  if (o && typeof o === 'object') {
    const id = o.id ?? o.value ?? o.name ?? o.label
    return { id: String(id), name: String(o.name ?? o.label ?? id) }
  }
  return { id: String(o), name: String(o) }
}

const attr = (s: string) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')

export function schemaForm(schema: FormSchema, access: FormAccess): SchemaBridge {
  const fields = new Map<string, FieldSchema>()
  const section = new Map<string, string>()
  const names = new Set<string>([schema.id, 'tabs'])
  for (const s of schema.sections) {
    if (!NAME.test(s.name) || names.has(s.name)) throw new Error(`formguide schema: bad or repeated name "${s.name}"`)
    names.add(s.name)
    for (const f of s.fields) {
      if (!NAME.test(f.name) || names.has(f.name)) throw new Error(`formguide schema: bad or repeated name "${f.name}"`)
      names.add(f.name)
      fields.set(f.name, f)
      section.set(f.name, s.name)
    }
  }
  if (!NAME.test(schema.id)) throw new Error(`formguide schema: bad form id "${schema.id}"`)

  const tabs = (schema.layout ?? 'tabs') === 'tabs' && schema.sections.length > 1
  const body = schema.sections.map((s) => {
    const inner = s.fields.map((f) => `    <${TAGS[f.type ?? 'text']} name="${attr(f.name)}" />`).join('\n')
    return tabs ? `  <Tab name="${attr(s.name)}">\n${inner}\n  </Tab>` : `  <Section name="${attr(s.name)}">\n${inner}\n  </Section>`
  }).join('\n')
  const jsx = `<Form name="${attr(schema.id)}">\n${tabs ? `<Tabs name="tabs">\n${body}\n</Tabs>` : body}\n</Form>`

  const optionsOf = (f: FieldSchema, values: Values) => (rule(f.options, values, [] as Option[]) ?? []).map(normOption)

  /** The form's value -> formguide's: choices as {id, name}. */
  const toConfig = (f: FieldSchema, v: unknown, opts: { id: string; name: string }[]): unknown => {
    if (!CHOICE.has(f.type ?? 'text') || v === undefined || v === null || v === '') return v ?? null
    const one = (x: unknown) => {
      if (x && typeof x === 'object') return normOption(x as Option)
      return opts.find((o) => o.id === String(x) || o.name === String(x)) ?? { id: String(x), name: String(x) }
    }
    return f.type === 'multiselect' ? (Array.isArray(v) ? v : [v]).map(one) : one(v)
  }

  /** formguide's value -> the form's own format (valueAs). */
  const toForm = (f: FieldSchema, v: unknown): unknown => {
    if (!CHOICE.has(f.type ?? 'text') || v === null || v === undefined) return v
    const as = f.valueAs ?? 'id'
    const one = (x: unknown) => {
      const o = normOption(x as Option)
      return as === 'option' ? o : as === 'name' ? o.name : o.id
    }
    return f.type === 'multiselect' ? (Array.isArray(v) ? v : [v]).map(one) : one(v)
  }

  const config = (): FormState['config'] => {
    const values = access.getValues() ?? {}
    const errors = access.getErrors?.() ?? {}
    const props: Record<string, Record<string, unknown>> = { [schema.id]: { label: schema.title ?? schema.id } }
    const state: Record<string, unknown> = {}
    if (tabs) props.tabs = {}
    for (const s of schema.sections) {
      const shown = rule(s.visible, values, true)
      let allDisabled = s.fields.length > 0
      for (const f of s.fields) {
        const opts = CHOICE.has(f.type ?? 'text') ? optionsOf(f, values) : null
        const disabled = rule(f.disabled, values, false)
        allDisabled &&= disabled
        props[f.name] = {
          label: f.label ?? f.name,
          visible: shown && rule(f.visible, values, true),
          disabled,
          required: rule(f.required, values, false),
          ...(f.readonly ? { readonly: true } : {}),
          ...(f.placeholder || f.help ? { placeholder: f.placeholder ?? f.help } : {}),
          ...(opts ? { options: opts } : {}),
          ...(errors[f.name] ? { error: errors[f.name] } : {}),
        }
        state[f.name] = toConfig(f, values[f.name], opts ?? [])
      }
      props[s.name] = { label: s.label ?? s.name, visible: shown, ...(allDisabled ? { disabled: true } : {}) }
    }
    return { props, state }
  }

  const apply = async (changes: Record<string, unknown>) => {
    for (const [name, v] of Object.entries(changes)) {
      const f = fields.get(name)
      if (!f) { console.warn(`formguide schema: no field "${name}"`); continue }
      await access.setValue(name, toForm(f, v))
    }
    await new Promise((r) => setTimeout(r, 0))   // let the form library settle (validation, re-render)
    return config()
  }

  return { jsx, config, apply, sectionOf: (f) => section.get(f), fields }
}

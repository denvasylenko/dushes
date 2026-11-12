import { describe, expect, it, vi } from 'vitest'
import { schemaForm, type FormSchema } from '../src/formguide/schema'
import { flatErrors } from '../src/rhf'

const MODELS: Record<string, string[]> = { toyota: ['Camry', 'Corolla'], kia: ['Rio'] }

const schema: FormSchema = {
  id: 'car_loan',
  title: 'Car loan',
  sections: [
    { name: 'applicant', label: 'Applicant', fields: [
      { name: 'first_name', label: 'First name', required: true },
      { name: 'phone', label: 'Phone', help: '10 digits' },
      { name: 'consent', label: 'I agree', type: 'bool' },
    ] },
    { name: 'car', label: 'Car', fields: [
      { name: 'car_make', label: 'Make', type: 'select', options: [{ value: 'toyota', label: 'Toyota' }, { value: 'kia', label: 'Kia' }] },
      { name: 'car_model', label: 'Model', type: 'select', options: (v) => MODELS[String(v.car_make)] ?? [], disabled: (v) => !v.car_make },
      { name: 'extras', label: 'Extras', type: 'multiselect', options: ['Winter tyres', 'Insurance'], valueAs: 'name' },
      { name: 'price', label: 'Price', type: 'number' },
    ] },
  ],
}

function fake(values: Record<string, unknown> = {}) {
  const state: Record<string, unknown> = { ...values }
  const setValue = vi.fn((name: string, v: unknown) => { state[name] = v })
  const errors: Record<string, string> = {}
  return { state, setValue, errors, bridge: schemaForm(schema, { getValues: () => state, setValue, getErrors: () => errors }) }
}

describe('schemaForm', () => {
  it('builds a JSX skeleton with the default tags', () => {
    const { bridge } = fake()
    expect(bridge.jsx).toContain('<Form name="car_loan">')
    expect(bridge.jsx).toContain('<Tabs name="tabs">')
    expect(bridge.jsx).toContain('<Tab name="car">')
    expect(bridge.jsx).toContain('<Dropdown name="car_make" />')
    expect(bridge.jsx).toContain('<MultiSelect name="extras" />')
    expect(bridge.jsx).toContain('<Checkbox name="consent" />')
    expect(bridge.jsx).toContain('<NumberInput name="price" />')
  })

  it('evaluates rules against the current values and converts choices to options', () => {
    const { bridge, state, errors } = fake({ car_make: 'toyota', extras: ['Insurance'] })
    errors.phone = 'Must be 10 digits'
    const c = bridge.config()
    expect(c.props!.car_model.options).toEqual([{ id: 'Camry', name: 'Camry' }, { id: 'Corolla', name: 'Corolla' }])
    expect(c.props!.car_model.disabled).toBe(false)
    expect(c.state!.car_make).toEqual({ id: 'toyota', name: 'Toyota' })
    expect(c.state!.extras).toEqual([{ id: 'Insurance', name: 'Insurance' }])
    expect(c.props!.phone).toMatchObject({ error: 'Must be 10 digits', placeholder: '10 digits' })
    expect(c.props!.first_name.required).toBe(true)
    expect(c.props!.car).toMatchObject({ label: 'Car', visible: true })
    state.car_make = undefined
    expect(bridge.config().props!.car_model).toMatchObject({ disabled: true, options: [] })
  })

  it('applies card values in the form format', async () => {
    const { bridge, setValue } = fake()
    const next = await bridge.apply({ car_make: { id: 'kia', name: 'Kia' }, extras: [{ id: 'Winter tyres', name: 'Winter tyres' }], price: 1200000, nope: 1 })
    expect(setValue).toHaveBeenCalledWith('car_make', 'kia')                      // valueAs id (default)
    expect(setValue).toHaveBeenCalledWith('extras', ['Winter tyres'])             // valueAs name
    expect(setValue).toHaveBeenCalledWith('price', 1200000)
    expect(setValue).not.toHaveBeenCalledWith('nope', expect.anything())
    expect(next.props!.car_model.options).toEqual([{ id: 'Rio', name: 'Rio' }])  // the dependent list follows
  })

  it('rejects repeated or bad names', () => {
    expect(() => schemaForm({ id: 'f', sections: [{ name: 's', fields: [{ name: 'a' }, { name: 'a' }] }] }, { getValues: () => ({}), setValue: () => {} }))
      .toThrow(/repeated/)
    expect(() => schemaForm({ id: 'f', sections: [{ name: 's', fields: [{ name: 'a"b' }] }] }, { getValues: () => ({}), setValue: () => {} }))
      .toThrow(/bad/)
  })

  it('uses sections instead of tabs when asked', () => {
    const b = schemaForm({ ...schema, layout: 'sections' }, { getValues: () => ({}), setValue: () => {} })
    expect(b.jsx).not.toContain('<Tabs')
    expect(b.jsx).toContain('<Section name="applicant">')
    expect(b.sectionOf('car_model')).toBe('car')
  })
})

describe('flatErrors', () => {
  it('flattens react-hook-form errors', () => {
    expect(flatErrors({ phone: { type: 'pattern', message: 'Must be 10 digits' }, address: { city: { type: 'required', message: '' } } }))
      .toEqual({ phone: 'Must be 10 digits', 'address.city': 'required' })
  })
})

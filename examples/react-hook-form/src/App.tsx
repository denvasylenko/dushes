/**
 * An ordinary react-hook-form form with the formguide chat next to it.
 * The form knows nothing about the chat; the only glue is the schema and one hook.
 */
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { DateInput, NumberInput, Select } from './controls'
import { AguiChat } from '@formguide/agui-chat/react'
import { useFormguide, type FormSchema } from '@formguide/agui-chat/react-hook-form'

interface CarLoan {
  first_name: string; last_name: string; phone: string; birth_date: string
  employment: string; income: number | null
  car_make: string; car_model: string; car_year: number | null; car_price: number | null; extras: string[]
  term: string; consent: boolean
}

const MAKES = [{ id: 'toyota', name: 'Toyota' }, { id: 'kia', name: 'Kia' }, { id: 'skoda', name: 'Skoda' }]
const MODELS: Record<string, string[]> = { toyota: ['Camry', 'Corolla', 'RAV4'], kia: ['Rio', 'Sportage'], skoda: ['Octavia', 'Kodiaq'] }
const TERMS = ['12', '36', '60', '84']
const EXTRAS = ['Winter tyres', 'Insurance', 'Extended warranty']

// What the agent knows about the form: sections, labels, options and the rules, as functions of the values.
const schema: FormSchema = {
  id: 'rhf_car_loan',
  title: 'Car loan',
  domain: {
    title: 'Car loan',
    persona: 'You help a customer fill in a short car loan application. Plain language, brief answers.',
    starters: ['Where do I start?', 'I want a used Kia Sportage for 1.2 million', 'Which terms can I choose?'],
  },
  sections: [
    { name: 'applicant', label: 'Applicant', fields: [
      { name: 'first_name', label: 'First name', required: true },
      { name: 'last_name', label: 'Last name', required: true },
      { name: 'phone', label: 'Phone', required: true, help: '10 digits, no spaces' },
      { name: 'birth_date', label: 'Date of birth', type: 'date', required: true },
      { name: 'employment', label: 'Employment', type: 'radio', options: ['Employed', 'Self-employed', 'Retired'] },
      { name: 'income', label: 'Monthly income', type: 'number', required: (v) => v.employment !== 'Retired' },
    ] },
    { name: 'car', label: 'Car', fields: [
      { name: 'car_make', label: 'Make', type: 'select', options: MAKES, required: true },
      { name: 'car_model', label: 'Model', type: 'select', required: true,
        options: (v) => MODELS[String(v.car_make)] ?? [], disabled: (v) => !v.car_make },
      { name: 'car_year', label: 'Year', type: 'number' },
      { name: 'car_price', label: 'Price', type: 'number', required: true },
      { name: 'extras', label: 'Extras', type: 'multiselect', options: EXTRAS, valueAs: 'name' },
    ] },
    { name: 'loan', label: 'Loan', fields: [
      { name: 'term', label: 'Term, months', type: 'select', options: TERMS, required: true },
      { name: 'consent', label: 'I agree to a credit check', type: 'bool', required: true },
    ] },
  ],
}

const TABS = schema.sections.map((s) => ({ name: s.name, label: s.label ?? s.name }))

export function App() {
  const form = useForm<CarLoan>({ mode: 'onChange', defaultValues: { extras: [], consent: false } })
  const { register, watch, handleSubmit, control, formState: { errors } } = form
  const [tab, setTab] = useState('applicant')
  const [sent, setSent] = useState(false)
  const make = watch('car_make')

  // the whole integration: the form, its schema, and how to open a section
  const { plugins, ready, error } = useFormguide(form as never, schema, { onReveal: setTab })

  const field = (name: keyof CarLoan, label: string, input: React.ReactNode) => (
    <label className="field" data-name={name}>
      <span>{label}</span>
      {input}
      {errors[name] && <em role="alert">{String(errors[name]?.message || 'Required')}</em>}
    </label>
  )

  return (
    <div className="page">
      <main>
        <h1>Car loan</h1>
        <p className="lead">A plain react-hook-form form. The assistant on the right reads it, proposes values and shows fields.</p>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.name} role="tab" aria-selected={tab === t.name} className={tab === t.name ? 'on' : ''} onClick={() => setTab(t.name)}>{t.label}</button>
          ))}
        </nav>
        <form onSubmit={handleSubmit(() => setSent(true))}>
          <section hidden={tab !== 'applicant'}>
            {field('first_name', 'First name', <input className="ctl-field" {...register('first_name', { required: 'Required' })} />)}
            {field('last_name', 'Last name', <input className="ctl-field" {...register('last_name', { required: 'Required' })} />)}
            {field('phone', 'Phone', <input className="ctl-field" inputMode="numeric" {...register('phone', { required: 'Required', pattern: { value: /^\d{10}$/, message: 'Must be 10 digits' } })} />)}
            {field('birth_date', 'Date of birth', <Controller name="birth_date" control={control} rules={{ required: 'Required' }} render={({ field: f }) => (
              <DateInput id="birth_date" value={f.value} max={new Date().toISOString().slice(0, 10)} onChange={f.onChange} invalid={!!errors.birth_date} />)} />)}
            <fieldset className="field" data-name="employment">
              <span>Employment</span>
              <div className="row">{['Employed', 'Self-employed', 'Retired'].map((o) => (
                <label key={o} className="radio"><input type="radio" value={o} {...register('employment')} /> {o}</label>
              ))}</div>
            </fieldset>
            {field('income', 'Monthly income', <Controller name="income" control={control} render={({ field: f }) => (
              <NumberInput name="income" value={f.value ?? ''} step={1000} min={0} onChange={(v) => f.onChange(v === '' ? null : Number(v))} />)} />)}
          </section>
          <section hidden={tab !== 'car'}>
            {field('car_make', 'Make', (
              <Select {...register('car_make', { required: 'Required' })}>
                <option value="">Choose…</option>
                {MAKES.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </Select>
            ))}
            {field('car_model', 'Model', (
              <Select disabled={!make} {...register('car_model', { required: 'Required' })}>
                <option value="">{make ? 'Choose…' : 'Choose the make first'}</option>
                {(MODELS[make] ?? []).map((m) => <option key={m}>{m}</option>)}
              </Select>
            ))}
            {field('car_year', 'Year', <Controller name="car_year" control={control} render={({ field: f }) => (
              <NumberInput name="car_year" value={f.value ?? ''} min={1990} max={new Date().getFullYear()} onChange={(v) => f.onChange(v === '' ? null : Number(v))} />)} />)}
            {field('car_price', 'Price', <Controller name="car_price" control={control} rules={{ required: 'Required' }} render={({ field: f }) => (
              <NumberInput name="car_price" value={f.value ?? ''} step={50000} min={0} invalid={!!errors.car_price} onChange={(v) => f.onChange(v === '' ? null : Number(v))} />)} />)}
            <fieldset className="field" data-name="extras">
              <span>Extras</span>
              <div className="row">{EXTRAS.map((o) => (
                <label key={o} className="radio"><input type="checkbox" value={o} {...register('extras')} /> {o}</label>
              ))}</div>
            </fieldset>
          </section>
          <section hidden={tab !== 'loan'}>
            {field('term', 'Term, months', (
              <Select {...register('term', { required: 'Required' })}>
                <option value="">Choose…</option>
                {TERMS.map((t) => <option key={t}>{t}</option>)}
              </Select>
            ))}
            <label className="field check" data-name="consent">
              <input type="checkbox" {...register('consent', { required: 'Required' })} /> I agree to a credit check
            </label>
            <button className="submit" type="submit">{sent ? 'Sent ✓' : 'Send application'}</button>
          </section>
        </form>
        <details className="values"><summary>Form values (react-hook-form)</summary><pre>{JSON.stringify(watch(), null, 2)}</pre></details>
      </main>
      <aside>
        {error && <p className="err">The assistant is not available: {error}. Is the demo server running on port 8000?</p>}
        {ready && <AguiChat url="/agent/run" mode="inline" title="Car loan" subtitle="formguide · AI assistant, can make mistakes" plugins={plugins} />}
      </aside>
    </div>
  )
}

/**
 * The no-UI demo's static data: the sample requests and the form's fields, with no browser code, so the page can
 * read them at build time. The option objects and the field list repeat src/demo/form.ts (the landing_loan form);
 * headless.ts checks at run time that they still match it.
 */
const EMPLOYMENT = [{ id: 'employed', name: 'Employed' }, { id: 'self', name: 'Self-employed' }, { id: 'retired', name: 'Retired' }]
const LOAN_TYPES = [{ id: 'auto', name: 'Car loan' }, { id: 'personal', name: 'Personal loan' }, { id: 'mortgage', name: 'Mortgage' }]
const TERMS = ['12', '24', '36', '48', '60'].map((m) => ({ id: m, name: `${m} months` }))

export interface Sample { id: string; label: string; text: string; values: Record<string, unknown> }

export const SAMPLES: Sample[] = [
  {
    id: 'car', label: 'Car loan',
    text: 'Car loan for Alex Morgan, alex.morgan@example.com. Employed, takes home $6,200 a month. Wants $28,000 over 36 months for a Toyota.',
    values: { full_name: 'Alex Morgan', email: 'alex.morgan@example.com', employment: EMPLOYMENT[0], monthly_income: 6200, loan_type: LOAN_TYPES[0], car_make: { id: 'toyota', name: 'Toyota' }, amount: 28000, term: TERMS[2] },
  },
  {
    id: 'personal', label: 'Personal loan',
    text: 'Personal loan, $9,500 over 24 months. Applicant: Dana Lee, dana.lee@example.com, self-employed, about $4,100 a month after tax.',
    values: { full_name: 'Dana Lee', email: 'dana.lee@example.com', employment: EMPLOYMENT[1], monthly_income: 4100, loan_type: LOAN_TYPES[1], amount: 9500, term: TERMS[1] },
  },
  {
    id: 'partial', label: 'Half the data',
    text: 'Mortgage enquiry from Sam Okafor (sam.okafor@example.com), retired. No amount yet.',
    values: { full_name: 'Sam Okafor', email: 'sam.okafor@example.com', employment: EMPLOYMENT[2], loan_type: LOAN_TYPES[2] },
  },
]

export const FIELDS = [
  { name: 'full_name', label: 'Full name', required: true },
  { name: 'email', label: 'Email', required: true },
  { name: 'employment', label: 'Employment', required: false },
  { name: 'monthly_income', label: 'Monthly income', required: false },
  { name: 'loan_type', label: 'Loan type', required: true },
  { name: 'car_make', label: 'Car make', required: false },
  { name: 'amount', label: 'Amount', required: false },
  { name: 'term', label: 'Term', required: false },
]
export const LABEL: Record<string, string> = Object.fromEntries(FIELDS.map((f) => [f.name, f.label]))

/** A value as a person reads it: a choice by its name. */
export const display = (v: unknown): string =>
  v === null || v === undefined || v === '' ? '' : typeof v === 'number' ? v.toLocaleString('en-US') : typeof v === 'object' ? String((v as { name?: unknown }).name ?? JSON.stringify(v)) : String(v)

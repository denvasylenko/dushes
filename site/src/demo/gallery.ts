/**
 * The card gallery: every card formguide's chat can show, as a specimen. Each specimen is a real <agui-chat>
 * with the formguide plugin and a tiny agent that replays one recorded server event, so what you see and tap
 * is the shipped renderer. `event` is exactly the CUSTOM event the server sends; the answer is shown as the
 * widget sends it back (`forwardedProps.command.resume`).
 */
import type { AguiEvent, RunAgentInput } from '../../../packages/agui-chat/src/types'
import type { FormguideOptions } from '../../../packages/agui-chat/src/formguide/index'

export interface Specimen {
  id: string
  group: string
  /** the card type and variant, as a developer finds it in the event */
  tag: string
  title: string
  blurb: string
  /** what the user says to get this card */
  user: string
  /** the agent's sentence before the card */
  lead?: string
  /** the event the server sends */
  event: { name: string; value: unknown }
  /** what the agent does after the answer (default: a short acknowledgement) */
  after?: (resume: Record<string, unknown>, cardId: string) => AguiEvent[]
  /** host callbacks this card uses */
  opts?: Partial<FormguideOptions>
  /** the form's values before the card */
  state?: Record<string, unknown>
}

export const GROUPS = [
  { id: 'fill', title: 'Fill fields', blurb: 'The agent proposes values; the user checks them and fills them in with one tap.' },
  { id: 'ask', title: 'Ask', blurb: 'A question tied to a field fills it when answered. No second card.' },
  { id: 'pick', title: 'Dates, times and numbers', blurb: 'Our own pickers: the right control for the value, never the browser’s.' },
  { id: 'finish', title: 'Files and finishing', blurb: 'Ask for a document, show what is left, confirm what cannot be undone.' },
  { id: 'reply', title: 'In the reply', blurb: 'Not cards, but part of the answer: where it came from, and what to tap next.' },
  { id: 'catalog', title: 'Every block, live', blurb: 'Each tile is one block in a card, drawn by the shipped widget. Replay draws it again; the event shows its keys.' },
  { id: 'blocks', title: 'Your own cards', blurb: 'Cards composed from small blocks: you lay them out in formguide.yaml, the model fills the data, they look like ours.' },
]

const ask = (v: Record<string, unknown>) => ({ name: 'on_interrupt', value: { type: 'ask', card_id: 'q1', allow_text: false, ...v } })
const day = (d: number) => { const x = new Date(); x.setDate(x.getDate() + d); return x.toISOString().slice(0, 10) }
const months = (amount: number, n: number) => { const r = 0.069 / 12; return Math.round((amount * r) / (1 - (1 + r) ** -n)) }
const BANKS = ['Atlas Bank', 'Baltic Savings', 'Cedar Trust', 'Delta Credit', 'Evergreen Bank', 'First Harbor', 'Granite Mutual', 'Horizon Bank',
  'Ironwood Credit', 'Juniper Bank', 'Keystone Savings', 'Lakeside Bank', 'Meridian Trust', 'Northgate Bank', 'Oakridge Credit', 'Pioneer Bank',
  'Quarry Savings', 'Riverside Bank', 'Summit Trust', 'Tidewater Bank']

const GALLERY: Specimen[] = [
  // ------------------------------------------------------------ fill
  {
    id: 'set-fields', group: 'fill', tag: 'set_fields',
    title: 'Field changes',
    blurb: 'Values with the reason for each. Untick a row or tap a value to edit it; one button fills them all, and Undo stays on the result line.',
    user: 'Fill it in from my profile',
    lead: 'I found **4 values** in your profile.',
    state: { email: 'alex@old-mail.example' },
    event: { name: 'on_interrupt', value: { type: 'set_fields', card_id: 'c1', changes: [
      { name: 'full_name', label: 'Full name', kind: 'text', value: 'Alex Morgan', display: 'Alex Morgan', reason: 'From your profile' },
      { name: 'email', label: 'Email', kind: 'text', value: 'alex.morgan@example.com', display: 'alex.morgan@example.com', reason: 'From your profile',
        previous: 'alex@old-mail.example', previous_display: 'alex@old-mail.example' },
      { name: 'monthly_income', label: 'Monthly income, $', kind: 'number', value: 6200, display: '6200', reason: 'Net salary from your last payslip' },
      { name: 'start_date', label: 'Employed since', kind: 'date', value: '2019-04-02', display: '2019-04-02', reason: 'From your profile' },
    ] } },
  },
  {
    id: 'document', group: 'fill', tag: 'set_fields · source: document',
    title: 'Values from a document',
    blurb: 'A scan the user attached, read on the server. A value the reader is unsure of is marked to check; a soft rule shows in its row with Why.',
    user: 'Here is my passport',
    lead: 'From your passport:',
    event: { name: 'on_interrupt', value: { type: 'set_fields', card_id: 'c1', source: { kind: 'document', title: 'Passport', found: 3 }, changes: [
      { name: 'passport_no', label: 'Passport number', kind: 'text', value: '4512123456', display: '4512123456', reason: 'From the photo' },
      { name: 'birth_date', label: 'Date of birth', kind: 'date', value: '1990-05-31', display: '1990-05-31', reason: 'From the photo' },
      { name: 'issued_by', label: 'Issued by', kind: 'text', value: 'Lyon prefecture', display: 'Lyon prefecture', reason: 'From the photo', confidence: 'low',
        issue: { severity: 'warning', message: 'Check the spelling', why: 'The stamp is partly covered on the photo.' } },
    ] } },
  },
  {
    id: 'consent', group: 'fill', tag: 'set_fields · consent',
    title: 'Consents',
    blurb: 'Never pre-ticked. The user can read the text before agreeing, and the button says what is still required.',
    user: 'What do I need to agree to?',
    lead: 'Two consents are left. The first is required.',
    event: { name: 'on_interrupt', value: { type: 'set_fields', card_id: 'c1', changes: [
      { name: 'c_credit', label: 'Credit check', kind: 'bool', value: true, display: 'yes', consent: true, required: true,
        doc: { text: 'We check your credit history with the national bureau. This does not change your score.' } },
      { name: 'c_offers', label: 'Offers by email', kind: 'bool', value: true, display: 'yes', consent: true, required: false },
    ] } },
  },

  // ------------------------------------------------------------ ask
  {
    id: 'chips', group: 'ask', tag: 'ask · options',
    title: 'A choice of a few',
    blurb: 'Two to five short options are chips. With `field` and `applies`, the tap fills the field. On a computer, 1-9 pick an option.',
    user: 'Help me choose the loan type',
    event: ask({ question: 'Which **loan type**?', field: 'loan_type', label: 'Loan type', applies: true,
      options: [{ id: 'car', label: 'Car loan', value: 'car' }, { id: 'personal', label: 'Personal loan', value: 'personal' }, { id: 'home', label: 'Home improvement', value: 'home' }] }),
  },
  {
    id: 'yesno', group: 'ask', tag: 'ask · field: bool',
    title: 'Yes or no',
    blurb: 'A question about a checkbox field becomes two chips that tick or untick it. Never a decision asked in prose.',
    user: 'Do I need insurance?',
    lead: 'It is optional. It covers the payments if you cannot work for more than 30 days.',
    event: ask({ question: 'Add **payment insurance**?', field: 'insurance', label: 'Payment insurance', applies: true,
      options: [{ id: 'yes', label: 'Yes', value: true }, { id: 'no', label: 'No', value: false }] }),
  },
  {
    id: 'details', group: 'ask', tag: 'ask · options with description',
    title: 'Options with details',
    blurb: 'When options need a line of explanation, they become rows. Still one tap.',
    user: 'Which loan suits me?',
    event: ask({ question: 'What is the loan **for**?', field: 'purpose', label: 'Purpose', applies: true, options: [
      { id: 'car', label: 'A car', description: 'Car loan from 6.9% APR, the car as security', value: 'car' },
      { id: 'repairs', label: 'Repairs at home', description: 'Personal loan from 9.4%, no security', value: 'repairs' },
      { id: 'other', label: 'Something else', description: 'We will ask a few more questions', value: 'other' },
    ] }),
  },
  {
    id: 'compare', group: 'ask', tag: 'ask · options with attrs',
    title: 'A comparison',
    blurb: 'Options with the same attributes line up as a table. `recommended` marks the best fit, `sources` say where the numbers come from.',
    user: 'Compare the terms for me',
    event: ask({ question: 'Which **term**?', field: 'term', label: 'Term', applies: true, recommended: '36', sources: [{ title: 'Tariffs 2026' }],
      options: [24, 36, 60].map((m) => ({ id: String(m), label: `${m} months`, value: m,
        attrs: { Monthly: `$${months(28000, m).toLocaleString('en-US')}`, 'Total interest': `$${(months(28000, m) * m - 28000).toLocaleString('en-US')}` } })) }),
  },
  {
    id: 'search', group: 'ask', tag: 'ask · many options',
    title: 'A long list',
    blurb: 'More than twelve options get a search box; `suggested` options come first.',
    user: 'Where do I get my salary?',
    event: ask({ question: 'Which **bank** pays your salary?', field: 'salary_bank', label: 'Salary bank', applies: true, suggested: ['b7', 'b12'],
      options: BANKS.map((b, i) => ({ id: `b${i}`, label: b, value: b })) }),
  },
  {
    id: 'multi', group: 'ask', tag: 'ask · multiple',
    title: 'Several answers',
    blurb: 'Chips that toggle, and one button that says how many are picked.',
    user: 'What income do you count?',
    event: ask({ question: 'Which **incomes** do you have?', multiple: true, options: [
      { id: 'salary', label: 'Salary' }, { id: 'freelance', label: 'Freelance' }, { id: 'rent', label: 'Rent' }, { id: 'pension', label: 'Pension' }] }),
  },
  {
    id: 'several', group: 'ask', tag: 'ask · fields',
    title: 'Two or three short fields',
    blurb: 'Values that belong together are typed in one card. Enter moves to the next field and fills them all on the last.',
    user: 'Add my name as in the passport',
    event: ask({ question: 'Your **name**, as in the passport', allow_text: true,
      fields: [{ name: 'first_name', label: 'First name' }, { name: 'last_name', label: 'Last name' }] }),
  },

  // ------------------------------------------------------------ pick
  {
    id: 'date-ahead', group: 'pick', tag: 'ask · input.type: date',
    title: 'A day ahead',
    blurb: 'Quick picks for the next days, and the calendar one tap away.',
    user: 'When can you call me?',
    event: ask({ question: 'When should we **call** you?', field: 'call_date', label: 'Call date', applies: true, allow_text: true,
      input: { type: 'date', min: day(0) } }),
  },
  {
    id: 'date-past', group: 'pick', tag: 'ask · input.type: date, max',
    title: 'A date in the past',
    blurb: 'A founding date or a birthday opens the calendar right away. Tap the title for years, then months.',
    user: 'Fill in when the company was founded',
    event: ask({ question: 'When was the **company founded**?', field: 'founded', label: 'Founded', applies: true, allow_text: true,
      input: { type: 'date', max: day(-1) } }),
  },
  {
    id: 'time', group: 'pick', tag: 'ask · input.type: time',
    title: 'A time slot',
    blurb: 'Free slots from your calendar (`getSlots`), or a grid every 30 minutes within `min` and `max`.',
    user: 'Book a call tomorrow',
    opts: { getSlots: () => ['09:30', '11:00', '14:30', '16:00'] },
    event: ask({ question: 'What **time** tomorrow?', field: 'call_time', label: 'Call time', applies: true, allow_text: true, input: { type: 'time' } }),
  },
  {
    id: 'stepper', group: 'pick', tag: 'ask · input.type: number (few steps)',
    title: 'A short range',
    blurb: 'Under ten steps: a stepper, with a live line your app computes (`preview`), then one Set button.',
    user: 'How many years should I take?',
    opts: { preview: (_f, v) => `$${months(28000, v * 12).toLocaleString('en-US')} a month` },
    state: { term_years: 3 },
    event: ask({ question: 'How many **years**?', field: 'term_years', label: 'Term', applies: true, previous: 3, allow_text: true,
      input: { type: 'number', min: 1, max: 7, step: 1, unit: 'years' } }),
  },
  {
    id: 'slider', group: 'pick', tag: 'ask · input.type: number (long range)',
    title: 'A long range',
    blurb: 'Ten steps or more: a slider for exploring, the result updating as you drag.',
    user: 'How much can I borrow?',
    opts: { preview: (_f, v) => `$${months(v, 36).toLocaleString('en-US')} a month over 36 months` },
    event: ask({ question: 'How much do you want to **borrow**, in dollars?', field: 'amount', label: 'Amount', applies: true, allow_text: true,
      input: { type: 'number', min: 5000, max: 60000, step: 1000 } }),
  },
  {
    id: 'address', group: 'pick', tag: 'ask · input.type: address',
    title: 'An address',
    blurb: 'Suggestions as you type, from your address service (`lookupAddress`). Type three letters.',
    user: 'Fill in my address',
    opts: { lookupAddress: (_f, q) => ['12 Rue de la République', '12 Rue Royale', '12 Rue de la Charité']
      .filter((s) => s.toLowerCase().includes(q.toLowerCase().replace(/^\d+\s*/, '')) || /^\d/.test(q))
      .map((s) => ({ label: s, detail: '69002 Lyon, France' })) },
    event: ask({ question: 'Your **home address**?', field: 'address', label: 'Address', applies: true, allow_text: true, input: { type: 'address' } }),
  },

  // ------------------------------------------------------------ finish
  {
    id: 'upload', group: 'finish', tag: 'upload',
    title: 'A document request',
    blurb: 'Drop or pick a file; on a phone, the camera comes first. The privacy note is yours (`attachments.privacy_note`).',
    user: 'Can you read my payslip?',
    event: { name: 'on_interrupt', value: { type: 'upload', card_id: 'u1', prompt: 'Add your last payslip: I will read the income from it.',
      accept: '.pdf,.png,.jpg', privacy: 'The file stays on our server; only the values reach the chat.' } },
  },
  {
    id: 'status', group: 'finish', tag: 'review · mode: status',
    title: 'What is left',
    blurb: 'Sections with what is still empty. A tap shows the section; the button continues with the next one.',
    user: 'How much is left?',
    event: { name: 'on_interrupt', value: { type: 'review', card_id: 'r1', mode: 'status', sections: [
      { name: 'applicant', label: 'Applicant', left: 0 }, { name: 'employment', label: 'Employment', left: 2 }, { name: 'loan', label: 'Loan', left: 1 }] } },
  },
  {
    id: 'review', group: 'finish', tag: 'review · mode: submit',
    title: 'Check before sending',
    blurb: 'Errors block the button until fixed; a fix the agent knows is one tap, with Undo. Warnings explain and let you go on.',
    user: 'Can I submit?',
    state: { phone: '+33 6 12 34 56' },
    event: { name: 'on_interrupt', value: { type: 'review', card_id: 'r1', mode: 'submit', issues: [
      { severity: 'error', field: 'phone', label: 'Phone', message: 'needs 9 digits after +33', fix: { value: '+33 6 12 34 56 78', display: '+33 6 12 34 56 78' }, reveal: [] },
      { severity: 'warning', field: 'car_year', label: 'Car', message: 'is 9 years old at the end of the loan', detail: 'The limit is 10 years.', source: { title: 'Lending policy' } },
    ] } },
  },
  {
    id: 'confirm', group: 'finish', tag: 'confirm',
    title: 'A confirmation',
    blurb: 'Only for what cannot be undone. The button names the action; a yes becomes the receipt, then one rating.',
    user: 'Submit it',
    event: { name: 'on_interrupt', value: { type: 'confirm', card_id: 'k1', title: 'Send the application?', confirm_label: 'Send application',
      details: [{ label: 'Amount', value: '$28,000' }, { label: 'Term', value: '36 months' }, { label: 'Monthly', value: `$${months(28000, 36).toLocaleString('en-US')}` }],
      consequence: 'The bank checks your credit history. You cannot change the application after this.' } },
    after: (resume, cardId) => resume.accepted === false ? [] : [
      { type: 'CUSTOM', name: 'receipt', value: { card_id: cardId, title: 'Application sent', number: '48-1192', eta: 'An answer within one working day' } } as AguiEvent],
  },

  // ------------------------------------------------------------ reply
  {
    id: 'sources', group: 'reply', tag: 'CUSTOM sources',
    title: 'Where it came from',
    blurb: 'Chips under an answer from your documents. A tap shows the quote.',
    user: 'Can I repay early?',
    lead: 'Yes. Early repayment is **free after the first 3 months**; before that it costs 1% of the amount repaid.',
    event: { name: 'sources', value: { items: [
      { title: 'Tariffs 2026', section: 'Early repayment', quote: 'Early repayment is free of charge after three months from the start of the loan.' },
      { title: 'Lending policy', section: '4.2 Fees', quote: 'Within the first three months the fee is 1% of the amount repaid.' }] } },
  },
  {
    id: 'suggestions', group: 'reply', tag: 'CUSTOM suggestions',
    title: 'Quick replies and action chips',
    blurb: 'Replies to tap instead of typing. A chip with `applies` fills its fields at once, with Undo, and never starts a turn.',
    user: 'Which loan suits me?',
    lead: 'For a car, the **Car loan** is cheaper: from 6.9% APR with the car as security.',
    event: { name: 'suggestions', value: { items: ['Set the loan type to Car loan', 'What does security mean?'],
      applies: [[{ name: 'loan_type', label: 'Loan type', value: 'car', previous: null }], null] } },
  },
  {
    id: 'blocks-question', group: 'blocks', tag: 'blocks · place, row, buttons',
    title: 'A question of your own',
    blurb: 'Declared as `barber_match` in `cards:` (wait: true): the model calls show_barber_match with the data, the turn waits, a tap answers {action, label, values}.',
    user: 'Book me with my usual barber',
    lead: 'Your last visit was with Maria.',
    event: { name: 'on_interrupt', value: { type: 'blocks', card_id: 'b1', name: 'barber_match', blocks: [
      { type: 'title', text: 'Is this your barber?' },
      { type: 'place', title: 'Maria Ivanova', subtitle: 'Barbershop on Arbat', rating: 4.9 },
      { type: 'row', label: 'Next free slot', value: 'Today, 16:30', icon: 'calendar' },
      { type: 'buttons', items: [{ id: 'yes', label: 'Yes, book Maria', style: 'primary' }, { id: 'no', label: 'Another barber' }] }] } },
  },
  {
    id: 'blocks-pick', group: 'blocks', tag: 'blocks · swatches, choice',
    title: 'A palette to pick',
    blurb: 'Swatches and chips return their choice in `values` with the button.',
    user: 'Make my site look nicer',
    event: { name: 'on_interrupt', value: { type: 'blocks', card_id: 'b2', name: 'styles', blocks: [
      { type: 'title', text: 'Pick a style for your site' },
      { type: 'swatches', name: 'palette', items: [
        { id: 'calm', label: 'Calm', colors: ['#1d1d1f', '#f5f5f7', '#0071e3'] },
        { id: 'warm', label: 'Warm', colors: ['#3b2a20', '#fbf3ea', '#e8590c'] },
        { id: 'fresh', label: 'Fresh', colors: ['#0f2e28', '#eefaf6', '#0a7f6f'] }] },
      { type: 'choice', name: 'mood', options: ['Lighter', 'Darker', 'Warmer'] },
      { type: 'buttons', items: [{ id: 'use', label: 'Use it', style: 'primary' }, { id: 'skip', label: 'Not now', style: 'plain' }] }] } },
  },
  {
    id: 'blocks-progress', group: 'blocks', tag: 'blocks · steps, progress',
    title: 'Steps left',
    blurb: 'A checklist with a progress bar; `{left}` in the title counts the open steps.',
    user: 'What is left before I share it?',
    event: { name: 'on_interrupt', value: { type: 'blocks', card_id: 'b3', name: 'todo', blocks: [
      { type: 'steps', title: '{left} steps left', items: [{ label: 'Phone number', done: true }, { label: 'Opening hours' }, { label: 'Address' }] },
      { type: 'progress', value: 1, max: 3 },
      { type: 'buttons', items: [{ id: 'hours', label: 'Add opening hours', style: 'primary' }, { id: 'later', label: 'Not now', style: 'plain' }] }] } },
  },
  {
    id: 'blocks-display', group: 'blocks', tag: 'CUSTOM card · stat, diff, links',
    title: 'A card to show',
    blurb: 'Declared with wait: false, it comes as a CUSTOM card event while the turn goes on. Links call, route, add to the calendar, share.',
    user: 'Move my haircut to Friday',
    lead: 'Done, you are booked for Friday.',
    event: { name: 'card', value: { type: 'blocks', name: 'visit', blocks: [
      { type: 'stat', value: 'Fri, 16:30', label: 'Haircut with Maria', tone: 'ok' },
      { type: 'diff', label: 'Moved', from: 'Thu, 12:00', to: 'Fri, 16:30' },
      { type: 'links', items: [
        { kind: 'calendar', label: 'Add to calendar', value: { title: 'Haircut with Maria', start: '2026-11-20T16:30:00', minutes: 45 } },
        { kind: 'route', label: 'Route to the barbershop', value: 'Arbat 12, Moscow' },
        { kind: 'call', label: 'Call the barbershop', value: '+7 495 000 00 00' }] }] } },
  },
]

GALLERY.push({
  id: 'picker', group: 'blocks', tag: 'picker · groups, depends, fields',
  title: 'A booking',
  blurb: 'A `picker` card: one choice per group, times follow the day, "Other days" in place, and the button waits, saying what is missing.',
  user: 'Book a table for Friday',
  event: { name: 'on_interrupt', value: { type: 'picker', card_id: 'pk1', title: 'Book a table', submit: { label: 'Book' },
    groups: [
      { name: 'day', label: 'Day', options: [{ id: 'fri', label: 'Fri 20' }, { id: 'sat', label: 'Sat 21', off: 'Closed' }], more: { label: 'Other days', options: [{ id: 'sun', label: 'Sun 22' }, { id: 'mon', label: 'Mon 23' }] } },
      { name: 'time', label: 'Time' },
      { name: 'people', label: 'People', options: ['1', '2', '3', '4', '5+'], value: '2' }],
    depends: { time: { on: 'day', options: { fri: ['18:00', '19:30', '21:00'], sun: ['12:00', '14:00'], mon: ['19:00'] } } },
    fields: [{ name: 'phone', label: 'Phone', input: 'tel', required: true }] } },
})

/** One specimen per block, for the Blocks page (group "catalog"); the card gallery leaves them out. */
const block = (id: string, title: string, blurb: string, blocks: Record<string, unknown>[]): Specimen => ({
  id: `block-${id}`, group: 'catalog', tag: `block · ${id}`, title, blurb, user: `Show the ${id} block`,
  event: { name: 'on_interrupt', value: { type: 'blocks', card_id: `bk-${id}`, name: id, blocks } },
})
const done = { type: 'buttons', items: [{ id: 'ok', label: 'Done', style: 'primary' }] }
export const CATALOG: Specimen[] = [
  block('title', 'Title', '`text`, `subtitle?`: the card’s question.', [{ type: 'title', text: 'Is this your barber?', subtitle: 'From your last visit' }, done]),
  block('text', 'Text', '`text` with inline **markdown**, `tone?`.', [{ type: 'text', text: 'Your booking is **confirmed**. Maria will meet you at the door.' }, { type: 'text', text: 'Cancelled by the shop.', tone: 'danger' }, done]),
  block('note', 'Note', '`text`: a small grey line.', [{ type: 'title', text: 'Haircut' }, { type: 'note', text: 'Free cancellation up to 2 hours before.' }, done]),
  block('row', 'Rows', '`label`, `value`, `icon?`, `tone?`. Rows next to each other form one list.', [
    { type: 'row', label: 'Date', value: 'Fri, 20 Nov', icon: 'calendar' }, { type: 'row', label: 'Barber', value: 'Maria' },
    { type: 'row', label: 'Paid', value: '1 500 \u20bd', tone: 'ok' }, done]),
  block('place', 'Place or person', '`title`, `subtitle?`, `image?`, `rating?`.', [{ type: 'place', title: 'Maria Ivanova', subtitle: 'Barbershop on Arbat · 12 years', rating: 4.9 }, done]),
  block('image', 'Image', '`src` (https), `alt?`, `ratio?`.', [{ type: 'image', src: 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=800', alt: 'A barbershop chair', ratio: '16:9' }, done]),
  block('stat', 'Big number', '`value`, `label?`, `tone?`, `change?`, `spark?`.', [{ type: 'stat', value: '1 240 €', label: 'This month', change: '+12% vs October', spark: [700, 820, 780, 960, 1010, 1180, 1240] }, done]),
  block('diff', 'Was → now', '`label?`, `from`, `to`.', [{ type: 'diff', label: 'Moved', from: 'Thu, 12:00', to: 'Fri, 16:30' }, done]),
  block('steps', 'Steps', '`title?` ({left} counts open steps), `items: [{label, done?}]`.', [{ type: 'steps', title: '{left} steps left', items: [{ label: 'Phone number', done: true }, { label: 'Opening hours' }, { label: 'Address' }] }, done]),
  block('chart', 'Chart: columns', '`kind: bar`, `data: [{label, value}]`, `highlight?`: comparing a few amounts.', [{ type: 'chart', kind: 'bar', title: 'Visits by day', highlight: 'Sat',
    data: [['Mon', 12], ['Tue', 30], ['Wed', 18], ['Thu', 41], ['Fri', 26], ['Sat', 52], ['Sun', 9]].map(([label, value]) => ({ label, value })) }, done]),
  { ...block('chart', 'Chart: line', '`kind: line` (or `area`), `labels`, `series: [{name, data}]`, `unit?`: a change over time.', [{ type: 'chart', kind: 'line', title: 'Rate, 6 months', unit: '%',
    labels: ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'], series: [{ name: 'Rate', data: [17.2, 17.8, 17.5, 18.3, 18.6, 18.9] }] }, done]), id: 'block-chart-line' },
  { ...block('chart', 'Chart: bar list', '`kind: barList`: a ranking with long names.', [{ type: 'chart', kind: 'barList', title: 'Top services',
    data: [{ label: 'Haircut', value: 48 }, { label: 'Beard trim', value: 31 }, { label: 'Colour', value: 12 }] }, done]), id: 'block-chart-barlist' },
  { ...block('chart', 'Chart: parts of a whole', '`kind: stacked`: one bar of segments, each part’s share in the legend.', [{ type: 'chart', kind: 'stacked', title: 'Monthly payment',
    data: [{ label: 'Principal', value: 620 }, { label: 'Interest', value: 300 }, { label: 'Insurance', value: 80 }] }, done]), id: 'block-chart-stacked' },
  { ...block('chart', 'Chart: meter', '`kind: meter`, `value`, `max?`, `limit?`: a value against a limit.', [{ type: 'chart', kind: 'meter', title: 'Debt to income', value: 38, limit: 50, unit: '%' }, done]), id: 'block-chart-meter' },
  block('progress', 'Progress', '`value`, `max?`, `label?`.', [{ type: 'progress', value: 2, max: 3, label: 'Profile 2 of 3' }, done]),
  block('swatches', 'Palettes', '`name`, `items: [{id, label?, colors}]`; the pick comes back in `values`.', [{ type: 'swatches', name: 'palette', items: [
    { id: 'calm', label: 'Calm', colors: ['#1d1d1f', '#f5f5f7', '#0071e3'] }, { id: 'warm', label: 'Warm', colors: ['#3b2a20', '#fbf3ea', '#e8590c'] }] },
    { type: 'buttons', items: [{ id: 'use', label: 'Use it', style: 'primary' }] }]),
  block('choice', 'Choice', '`name`, `options` (objects or strings), `multiple?`.', [{ type: 'choice', name: 'slot', options: ['16:30', '18:00', '19:30'] }, { type: 'buttons', items: [{ id: 'book', label: 'Book', style: 'primary' }] }]),
  block('field', 'Field', '`name`, `label?`, `input?`, `placeholder?`; the text comes back in `values`.', [{ type: 'field', name: 'wish', label: 'A wish for Maria', placeholder: 'Shorter on the sides' }, { type: 'buttons', items: [{ id: 'send', label: 'Send', style: 'primary' }] }]),
  block('hours', 'Opening hours', '`name`, `label?`, `value?: [{days, from, to}]`, `presets?`: presets, weekday chips, from–to.', [{ type: 'hours', name: 'hours', label: 'Opening hours' },
    { type: 'buttons', items: [{ id: 'save', label: 'Save', style: 'primary' }] }]),
  block('preview', 'Site preview', '`src`, `href?`, `ratio?` (16:10, 9:16): a live thumbnail, view only.', [{ type: 'preview', src: 'https://example.com/', href: 'https://example.com/', title: 'Your site', ratio: '16:10' }, done]),
  block('buttons', 'Buttons', '`items: [{id, label, style?}]`: primary, secondary, plain, danger.', [{ type: 'buttons', items: [
    { id: 'yes', label: 'Book', style: 'primary' }, { id: 'later', label: 'Later' }, { id: 'skip', label: 'Skip', style: 'plain' }, { id: 'cancel', label: 'Cancel visit', style: 'danger' }] }]),
  block('links', 'Links', '`items: [{kind, label, value}]`: call, route, web, calendar, share, copy, chat.', [{ type: 'links', items: [
    { kind: 'calendar', label: 'Add to calendar', value: { title: 'Haircut', start: '2026-11-20T16:30:00', minutes: 45 } },
    { kind: 'route', label: 'Route', value: 'Arbat 12, Moscow' }, { kind: 'call', label: 'Call', value: '+7 495 000 00 00' },
    { kind: 'copy', label: 'Copy the booking number', value: 'B-20431' }] }]),
  block('divider', 'Divider', 'A hairline between parts.', [{ type: 'text', text: 'Above' }, { type: 'divider' }, { type: 'text', text: 'Below' }, done]),
]

/** Every block alone, for the one-sheet overview at the top of the Blocks page: [type, blocks]. */
export const SHEET: [string, Record<string, unknown>[]][] = CATALOG.map((s) => {
  const blocks = ((s.event.value as { blocks: Record<string, unknown>[] }).blocks)
  const own = blocks.filter((b) => b !== done && !(b.type === 'buttons' && s.id !== 'block-buttons') && !(b.type === 'title' && s.id !== 'block-title'))
  return [s.id.replace(/^block-/, ''), own.length ? own : blocks]
})

export const SPECIMENS: Specimen[] = [...GALLERY, ...CATALOG]

let seq = 0
const nid = (p: string) => `${p}-${++seq}`

/** Plays a specimen: the card on the first run, a short reply after an answer or a typed message. */
export class GalleryAgent {
  private runs = 0
  constructor(private s: Specimen, private onResume: (r: Record<string, unknown>) => void) {}
  reset(): void { this.runs = 0 }

  run(input: RunAgentInput) {
    const resume = (input.forwardedProps as { command?: { resume?: Record<string, unknown> } } | undefined)?.command?.resume
    const first = this.runs++ === 0
    const s = this.s
    const events: AguiEvent[] = []
    const say = (text: string) => {
      const messageId = nid('m')
      events.push({ type: 'TEXT_MESSAGE_START', messageId, role: 'assistant' }, { type: 'TEXT_MESSAGE_CONTENT', messageId, delta: text },
        { type: 'TEXT_MESSAGE_END', messageId })
    }
    if (resume) {
      this.onResume(resume)
      const cardId = String((s.event.value as { card_id?: string }).card_id ?? '')
      const more = s.after?.(resume, cardId)
      if (more) events.push(...more)
      else say(resume.accepted === false ? 'No problem, nothing changed.' : 'Done.')
    } else if (first) {
      if (s.lead) say(s.lead)
      const value = s.event.name === 'on_interrupt' ? JSON.stringify(s.event.value) : s.event.value
      events.push({ type: 'CUSTOM', name: s.event.name, value } as AguiEvent)
    } else {
      say('This is a recorded card. Tap **Replay** to see it again.')
    }
    return {
      subscribe: (o: { next(e: AguiEvent): void; error(e: unknown): void; complete(): void }) => {
        let stopped = false
        const runId = nid('run')
        const t = setTimeout(() => {
          if (stopped) return
          o.next({ type: 'RUN_STARTED', threadId: input.threadId, runId })
          events.forEach((e) => o.next(e))
          o.next({ type: 'RUN_FINISHED', threadId: input.threadId, runId })
          o.complete()
        }, first && !resume ? 380 : 220)
        return { unsubscribe: () => { stopped = true; clearTimeout(t) } }
      },
    }
  }
}

/** The gallery has no server: uploads to this path succeed locally so the upload card can finish. */
export const FAKE_BASE = '/__gallery'
export function fakeUploads(): void {
  const Real = window.XMLHttpRequest
  if ((Real as unknown as { gallery?: boolean }).gallery) return
  class Fake extends Real {
    private fake = false
    open(method: string, url: string | URL, ...rest: unknown[]): void {
      this.fake = String(url).startsWith(FAKE_BASE)
      if (!this.fake) return (super.open as (...a: unknown[]) => void)(method, url, ...rest)
    }
    send(body?: Document | XMLHttpRequestBodyInit | null): void {
      if (!this.fake) return super.send(body)
      const file = body instanceof FormData ? body.get('file') : null
      let p = 0
      const tick = () => {
        p = Math.min(1, p + 0.25)
        this.upload.onprogress?.(new ProgressEvent('progress', { lengthComputable: true, loaded: p * 100, total: 100 }))
        if (p < 1) return void setTimeout(tick, 160)
        Object.defineProperty(this, 'status', { value: 200 })
        Object.defineProperty(this, 'responseText', { value: JSON.stringify({ id: 'att_demo', filename: file instanceof File ? file.name : 'file' }) })
        this.onload?.(new ProgressEvent('load'))
      }
      setTimeout(tick, 120)
    }
  }
  ;(Fake as unknown as { gallery: boolean }).gallery = true
  window.XMLHttpRequest = Fake as unknown as typeof XMLHttpRequest
}

/** Play a specimen in a chat element: the formguide plugin with a local form, the card on the first run.
 * `onAnswer` sees what the card sends back. Returns `replay()`. Used by the gallery and by Ask AI's live cards. */
export function playSpecimen(chat: import('../../../packages/agui-chat/src/element').AguiChatElement, s: Specimen,
  formguide: (o: FormguideOptions) => import('../../../packages/agui-chat/src/types').Plugin,
  onAnswer?: (resume: Record<string, unknown>) => void): { replay(): void } {
  fakeUploads()
  let state: Record<string, unknown> = { ...(s.state ?? {}) }
  const agent = new GalleryAgent(s, (r) => onAnswer?.(r))
  chat.agent = agent
  const plugin = formguide({
    getState: () => ({ config: { props: {}, state }, jsx_hash: 'gallery', form_id: 'loan_application', ui: null }),
    applyChanges: (changes) => { state = { ...state, ...changes }; return { props: {}, state } },
    onDirective: () => {},
    baseUrl: FAKE_BASE,
    undoSeconds: 60,
    onFeedback: () => {},
    ...(s.opts ?? {}),
  })
  delete plugin.restore   // no server: nothing to restore
  chat.use(plugin)
  const start = () => { void chat.send(s.user) }
  start()
  return { replay: () => { chat.stop(); chat.reset(); agent.reset(); state = { ...(s.state ?? {}) }; start() } }
}

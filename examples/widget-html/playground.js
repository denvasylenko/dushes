/* agui-chat playground: every setting of the chat in sections, a live preview, and the code to copy.
   One state object (S) drives the chat and the generated code, so what you see is what you copy.
   Sliders have safe ranges only (no 0 px padding, no unreadable sizes): every value they allow looks right. */
const chat = document.getElementById('chat')
const FORM_ID = 'barber_booking'

// ------------------------------------------------------------------ the widget's defaults (styles.ts)
const LIGHT = { accent: '#1d1d1f', 'on-accent': '#ffffff', link: '#0071e3', bg: '#ffffff', surface: '#fafafb', soft: '#f2f2f5', ink: '#1d1d1f',
  'ink-2': '#6e6e73', 'ink-3': '#86868b', line: '#ececf0', 'line-2': '#e3e3e8', ok: '#34c759', danger: '#ff3b30' }
const DARK = { accent: '#f5f5f7', 'on-accent': '#1d1d1f', link: '#4ea1ff', bg: '#1c1c1e', surface: '#242426', soft: '#2c2c2e', ink: '#f5f5f7',
  'ink-2': '#aeaeb2', 'ink-3': '#8e8e93', line: '#333336', 'line-2': '#3a3a3c', ok: '#34c759', danger: '#ff3b30' }
const COLORS = [
  ['accent', 'Accent', 'Main buttons, the logo, the launcher, selected chips and days'],
  ['on-accent', 'On accent', 'Text and icons on the accent'],
  ['link', 'Links', 'Links, Undo, Edit, Show, the focus ring'],
  ['bg', 'Panel', 'The chat window behind everything'],
  ['surface', 'Cards', 'Card backgrounds'],
  ['soft', 'Quiet fill', 'Your message bubble, input fields, code blocks'],
  ['ink', 'Text', 'Main text'],
  ['ink-2', 'Secondary text', 'Labels, captions'],
  ['ink-3', 'Hints', 'Placeholders, small hints'],
  ['line', 'Dividers', 'Lines between rows and around cards'],
  ['line-2', 'Borders', 'Borders of chips, inputs, the composer'],
  ['ok', 'Success', 'The tick after a card is applied'],
  ['danger', 'Danger', 'Errors, destructive buttons, the unread dot'],
]
const PRESETS = {
  default: { name: 'Default', desc: 'the widget\'s own quiet black and white; the accent is near-black in light and near-white in dark.', light: {}, dark: {} },
  contrast: { name: 'Contrast', desc: 'pure black and white with stronger lines and text and a thicker focus ring, for accessibility.', base: 'contrast', light: {}, dark: {} },
  // built-in theme packs (loaded on demand); sw: the swatches shown on the preset button
  glass: { name: 'Glass', desc: 'translucent frosted cards over a soft gradient, blue accents and bubbles, large radii: in the spirit of iOS.', base: 'glass', light: {}, dark: {},
    sw: ['#007aff', 'linear-gradient(160deg,#eef3ff,#fdf3ee)', 'rgba(255,255,255,.7)', '#007aff'] },
  bold: { name: 'Bold', desc: 'large radii, strong type and a vivid blue on clean cards; in dark, glassy cards over a deep glow: in the spirit of a fintech app.', base: 'bold', light: {}, dark: {},
    sw: ['#0a5cff', '#f2f3f5', '#ffffff', '#121214'] },
  messenger: { name: 'Messenger', desc: 'bubbles for both sides on a wallpaper, a light blue accent: in the spirit of a messenger.', base: 'messenger', light: {}, dark: {},
    sw: ['#3390ec', 'linear-gradient(135deg,#d4e6ad,#92c3d8)', '#e7fdd5', '#ffffff'] },
  ocean: { name: 'Ocean', desc: 'a calm blue accent.', light: { accent: '#0a66c2', link: '#0a66c2', soft: '#eaf2fb', surface: '#f7fafd' }, dark: { accent: '#4c9cf0', 'on-accent': '#071a2e', link: '#7cb7ff', bg: '#0f1720', surface: '#16212d', soft: '#1d2a38' } },
  forest: { name: 'Forest', desc: 'a fresh green accent.', light: { accent: '#0a7f6f', link: '#0a7f6f', soft: '#e7f4f1', surface: '#f7fbfa' }, dark: { accent: '#4fd1c1', 'on-accent': '#06201d', link: '#4fd1c1', bg: '#0f1514', surface: '#151d1c', soft: '#1b2726' } },
  sunset: { name: 'Sunset', desc: 'a warm orange accent.', light: { accent: '#e8590c', link: '#d9480f', soft: '#fff1e6', surface: '#fffaf5' }, dark: { accent: '#ff922b', 'on-accent': '#2b1300', link: '#ffa94d', bg: '#1d1611', surface: '#251c15', soft: '#2e231a' } },
  grape: { name: 'Grape', desc: 'a playful violet accent.', light: { accent: '#7048e8', link: '#6741d9', soft: '#f1edff', surface: '#faf8ff' }, dark: { accent: '#b197fc', 'on-accent': '#1a1033', link: '#b197fc', bg: '#17131f', surface: '#1f1a2a', soft: '#282236' } },
}
const FONTS = { system: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif', rounded: 'ui-rounded, "SF Pro Rounded", -apple-system, sans-serif',
  inter: '"Inter", -apple-system, sans-serif', serif: 'Georgia, "New York", serif', mono: 'ui-monospace, SFMono-Regular, Menlo, monospace' }

// ------------------------------------------------------------------ state
const S = {
  opt: { mode: 'inline', scheme: 'auto', lang: '', typing: 'words', toolSteps: true, quickReplies: true, mic: true, micAutoSend: false,
    dictation: 'browser', attach: true, attachMultiple: true, attachMaxMb: 20, bubbleSide: 'right', greeting: 'Want me to book you a haircut?', motion: 'spring',
    title: 'Barbershop', subtitle: 'formguide · playground', intro: '', placeholder: '', footnote: '' },
  preset: 'default', light: {}, dark: {},
  shape: { radius: 14, 'radius-sm': 10, 'radius-lg': 20, 'radius-pill': 999, font: 'system', 'panel-width': 460 },
  comp: {},                 // component tokens the user changed: {'card-bg': '#...'}
  parts: [],                // page CSS rules: [{part, bg, ink, border, radius, weight}]
  cards: { select: true, diff: true, reason: true, edit: true, jump: true, undo: true, undoSeconds: 20, cardSteps: false, exclude: [] },
  slots: { empty: false, user: false, assistant: false, header: false, launcher: false, error: false, suggestions: false, confirmCard: false },
  icon: 'spark',
}
const S0 = structuredClone(S)   // the start: what "your changes" are counted from

// ------------------------------------------------------------------ tiny DOM helper
function el(tag, props = {}, ...kids) {
  const e = document.createElement(tag)
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue
    if (k.startsWith('on')) e.addEventListener(k.slice(2), v)
    else if (k === 'class') e.className = v
    else if (k in e && typeof v !== 'string') e[k] = v
    else e.setAttribute(k, v === true ? '' : v)
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c instanceof Node ? c : document.createTextNode(String(c)))
  return e
}
const css = (e, s) => { e.style.cssText = s; return e }
const row = (name, help, ...ctl) => el('div', { class: 'row' }, el('span', { class: 'name' }, name), el('span', { class: 'ctl' }, ...ctl), help ? el('span', { class: 'help' }, help) : null)
const sw = (get, set) => el('input', { type: 'checkbox', class: 'switch', role: 'switch', checked: get(), onchange: (e) => { set(e.target.checked); update() } })
const seg = (choices, get, set) => {
  const box = el('span', { class: 'seg', role: 'radiogroup' })
  const draw = () => box.querySelectorAll('button').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.v === String(get()))))
  for (const [v, label] of choices) box.append(el('button', { type: 'button', role: 'radio', 'data-v': v, onclick: () => { set(v); draw(); update() } }, label))
  draw()
  return box
}
const pick = (choices, get, set) => el('select', { onchange: (e) => { set(e.target.value); update() } },
  choices.map(([v, label]) => el('option', { value: v, selected: String(get()) === v }, label)))
const text = (get, set, ph = '') => el('input', { type: 'text', value: get(), placeholder: ph, oninput: (e) => { set(e.target.value); update() } })

/** Show what a setting changes: a dashed outline on those parts in the preview for a moment (page CSS via ::part). */
let flashTimer = 0
function flash(parts) {
  if (!parts?.length) return
  if (S.opt.mode === 'inline' && !chat.shadowRoot?.querySelector('.card')) showExamples()
  let st = document.getElementById('pg-flash')
  if (!st) { st = el('style', { id: 'pg-flash' }); document.head.append(st) }
  st.textContent = parts.map((p) => `agui-chat::part(${p}) { outline: 2px dashed #ff9f0a !important; outline-offset: 2px; }`).join('\n')
  clearTimeout(flashTimer)
  flashTimer = setTimeout(() => { st.textContent = '' }, 1400)
}
/** A few cards in the preview so shape and colour changes have something to act on. */
let examplesShown = false
function showExamples() {
  if (examplesShown) return
  examplesShown = true
  void chat.showCard(structuredClone(SAMPLES.find(([n]) => n === 'Options with details')[1]))
  void chat.showCard(structuredClone(SAMPLES.find(([n]) => n === 'Field changes')[1]))
}
/** A slider with a safe range; `parts` are outlined in the preview while it moves. */
const slider = (min, max, get, set, unit = 'px', parts = null) => {
  const out = el('span', { class: 'val' }, `${get()}${unit}`)
  return [el('input', { type: 'range', min, max, value: Math.min(max, Math.max(min, get())), onpointerdown: () => flash(parts), onfocus: () => flash(parts),
    oninput: (e) => { set(Number(e.target.value)); out.textContent = `${e.target.value}${unit}`; update(); flash(parts) } }), out]
}
/** Buttons and chips: 8-32 px, and the last step is a capsule (999 px, the Apple default). */
function pillRow() {
  const CAP = 33
  const PILL = ['button', 'chip', 'send', 'fab', 'calendar-day', 'icon-button']
  const toUi = (v) => (v >= 999 ? CAP : Math.min(32, v))
  const show = (u) => (u >= CAP ? 'capsule' : `${u}px`)
  const out = el('span', { class: 'val' }, show(toUi(S.shape['radius-pill'])))
  const input = el('input', { type: 'range', min: 8, max: CAP, value: toUi(S.shape['radius-pill']), onpointerdown: () => flash(PILL), onfocus: () => flash(PILL), oninput: (e) => {
    const u = Number(e.target.value)
    S.shape['radius-pill'] = u >= CAP ? 999 : u
    out.textContent = show(u)
    update()
    flash(PILL)
  } })
  return row('Buttons, chips and round controls', 'Buttons (Fill in, Reject, Send), chips, the launcher, steppers and calendar days. Chips are the small rounded tap buttons: quick replies under an answer, options in a question card, starters on the empty chat. Far right: a capsule. To change only the buttons: Components › Buttons.', input, out)
}
/** A choice with a guide: the control, then every option with what it means; the chosen one is highlighted. */
function choice(name, intro, choices, get, set, kind = 'seg') {
  const guide = el('ul', { class: 'guide' })
  const draw = () => guide.replaceChildren(...choices.map(([v, label, desc]) =>
    el('li', { class: String(get()) === String(v) ? 'on' : '' }, el('b', {}, label), desc ? ` — ${desc}` : '')))
  const setAndDraw = (v) => { set(v); draw() }
  const ctl = kind === 'seg' ? seg(choices.map(([v, l]) => [v, l]), get, setAndDraw) : pick(choices.map(([v, l]) => [v, l]), get, setAndDraw)
  draw()
  return el('div', { class: 'row' }, el('span', { class: 'name' }, name), el('span', { class: 'ctl' }, ctl),
    el('div', { class: 'help' }, intro ? el('div', {}, intro) : null, guide))
}
const group = (title, ...rows) => [title ? el('div', { class: 'group-title' }, title) : null, el('div', { class: 'group' }, ...rows)]

// ------------------------------------------------------------------ samples for showCard()
const SAMPLES = [
  ['Field changes', { type: 'set_fields', changes: [
    { name: 'client_name', label: 'Your name', kind: 'text', value: 'Anna', display: 'Anna', reason: 'From your message', reveal: [] },
    { name: 'visit_date', label: 'Date', kind: 'date', value: '2026-11-20', display: '2026-11-20', previous: '2026-11-18', previous_display: '2026-11-18', reason: 'You moved the visit', reveal: [] }] }],
  ['Options with details', { type: 'ask', question: 'Which service?', allow_text: false, options: [
    { id: 'cut', label: 'Haircut', description: '45 min · from 1 500 ₽' }, { id: 'beard', label: 'Beard trim', description: '30 min · from 900 ₽' },
    { id: 'combo', label: 'Haircut and beard', description: '75 min · from 2 200 ₽' }] }],
  ['Comparison', { type: 'ask', question: 'Which barber?', allow_text: false, recommended: 'maria', options: [
    { id: 'maria', label: 'Maria', attrs: { Rating: '4.9', Next: 'Today 16:30' } }, { id: 'ivan', label: 'Ivan', attrs: { Rating: '4.7', Next: 'Tomorrow 10:00' } }] }],
  ['Long list', { type: 'ask', question: 'Which salon?', allow_text: false, suggested: ['s1', 's2'],
    options: Array.from({ length: 24 }, (_, i) => ({ id: `s${i + 1}`, label: `Salon ${['Arbat', 'Tverskaya', 'Patriki', 'Kitay-gorod'][i % 4]} ${i + 1}` })) }],
  ['Date', { type: 'ask', question: 'Which day?', input: { type: 'date' }, allow_text: true }],
  ['Date in the past', { type: 'ask', question: 'Your date of birth?', input: { type: 'date', max: new Date().toISOString().slice(0, 10) }, allow_text: true }],
  ['Time', { type: 'ask', question: 'What time?', input: { type: 'time', min: '10:00', max: '19:00' }, allow_text: true }],
  ['Stepper', { type: 'ask', question: 'How many people?', input: { type: 'number', min: 1, max: 6, step: 1 }, allow_text: true }],
  ['Several fields', { type: 'ask', question: 'Your contacts', allow_text: true, fields: [{ name: 'phone', label: 'Phone' }, { name: 'email', label: 'Email' }] }],
  ['Consents', { type: 'set_fields', changes: [
    { name: 'c_rules', label: 'I agree to the salon rules', kind: 'bool', value: true, display: 'yes', consent: true, required: true, doc: { text: 'Cancel at least 2 hours before the visit.' } },
    { name: 'c_sms', label: 'Reminders by SMS', kind: 'bool', value: true, display: 'yes', consent: true, required: false }] }],
  ['Form status', { type: 'review', mode: 'status', sections: [{ name: 'visit', label: 'Visit', left: 0 }, { name: 'contacts', label: 'Contacts', left: 2 }] }],
  ['Check before sending', { type: 'review', mode: 'submit', issues: [
    { severity: 'error', field: 'phone', label: 'Phone', message: 'needs 10 digits', fix: { value: '9001234567', display: '9001234567' } },
    { severity: 'warning', field: 'visit_time', label: 'Time', message: 'is close to closing', detail: 'The salon closes at 20:00.' }] }],
  ['File request', { type: 'upload', prompt: 'A photo of the haircut you want', accept: 'image/*', privacy: 'Only the barber sees it.' }],
  ['Confirmation', { type: 'confirm', title: 'Book the visit?', confirm_label: 'Book', details: [{ label: 'Service', value: 'Haircut' }, { label: 'When', value: 'Fri, 16:30' }],
    consequence: 'Maria gets a notification.' }],
  // cards from blocks: the developer lays them out, the model fills the data (formguide.yaml `cards:`)
  ['Blocks: your barber?', { type: 'blocks', name: 'barber_match', blocks: [
    { type: 'title', text: 'Is this your barber?', subtitle: 'From your last visit' },
    { type: 'place', title: 'Maria Ivanova', subtitle: 'Barbershop on Arbat · 12 years', rating: 4.9 },
    { type: 'row', label: 'Next free slot', value: 'Today, 16:30', icon: 'calendar' },
    { type: 'row', label: 'Haircut', value: 'from 1 500 ₽' },
    { type: 'buttons', items: [{ id: 'yes', label: 'Yes, book her', style: 'primary' }, { id: 'no', label: 'Another barber' }] }] }],
  ['Blocks: pick a style', { type: 'blocks', name: 'styles', blocks: [
    { type: 'title', text: 'Pick a style for your site' },
    { type: 'swatches', name: 'palette', items: [
      { id: 'calm', label: 'Calm', colors: ['#1d1d1f', '#f5f5f7', '#0071e3'] },
      { id: 'warm', label: 'Warm', colors: ['#3b2a20', '#fbf3ea', '#e8590c'] },
      { id: 'fresh', label: 'Fresh', colors: ['#0f2e28', '#eefaf6', '#0a7f6f'] }] },
    { type: 'choice', name: 'mood', options: [{ id: 'lighter', label: 'Lighter' }, { id: 'darker', label: 'Darker' }, { id: 'warmer', label: 'Warmer' }] },
    { type: 'buttons', items: [{ id: 'use', label: 'Use it', style: 'primary' }, { id: 'skip', label: 'Not now', style: 'plain' }] }] }],
  ['Blocks: steps left', { type: 'blocks', name: 'todo', blocks: [
    { type: 'steps', title: '{left} steps left before you share', items: [
      { label: 'Phone number', done: true }, { label: 'Opening hours', done: false }, { label: 'Address', done: false }, { label: 'Prices', done: false }] },
    { type: 'progress', value: 1, max: 4 },
    { type: 'buttons', items: [{ id: 'hours', label: 'Add opening hours', style: 'primary' }, { id: 'later', label: 'Not now', style: 'plain' }] }] }],
  ['Blocks: booked', { type: 'blocks', name: 'visit', blocks: [
    { type: 'stat', value: 'Fri, 16:30', label: 'Haircut with Maria', tone: 'ok' },
    { type: 'diff', label: 'Moved', from: 'Thu, 12:00', to: 'Fri, 16:30' },
    { type: 'links', items: [
      { kind: 'calendar', label: 'Add to calendar', value: { title: 'Haircut with Maria', start: '2026-11-20T16:30:00', minutes: 45, place: 'Arbat 12' } },
      { kind: 'route', label: 'Route to the barbershop', value: 'Arbat 12, Moscow' },
      { kind: 'call', label: 'Call the barbershop', value: '+7 495 000 00 00' },
      { kind: 'share', label: 'Share with a friend', value: 'https://example.com/booking/123' }] },
    { type: 'field', name: 'wish', label: 'A wish for Maria', placeholder: 'Shorter on the sides' },
    { type: 'buttons', items: [{ id: 'ok', label: 'Done', style: 'primary' }] }] }],
]
const sample = (name) => SAMPLES.find(([n]) => n === name)[1]
/** The answer, short: the form state the backend sends back is replaced by a note (it is your form, not the card's answer). */
function shortAnswer(a) {
  if (!a || typeof a !== 'object') return a
  const out = Array.isArray(a) ? [] : {}
  for (const [k, v] of Object.entries(a)) out[k] = k === 'config' ? '(your form state after the change)' : (v && typeof v === 'object' ? shortAnswer(v) : v)
  return out
}
async function showSample(payload, { fresh = false } = {}) {
  if (fresh) chat.reset()
  if (S.opt.mode !== 'inline') chat.open?.()
  const answer = await chat.showCard(structuredClone(payload))
  const box = document.getElementById('answer')
  const short = JSON.stringify(shortAnswer(answer))
  box.hidden = false
  document.getElementById('answer-sum').textContent = short.length > 70 ? `${short.slice(0, 70)}…` : short
  document.getElementById('answer-json').textContent = JSON.stringify(shortAnswer(answer), null, 2)
}

/** A scripted turn: the chat runs it like a real one (text, quick replies or an error), without the backend. */
function scripted(events) {
  return { run: () => ({ subscribe: (o) => {
    let stop = false
    ;(async () => {
      for (const e of [{ type: 'RUN_STARTED', threadId: 'pg', runId: 'pg' }, ...events]) {
        if (stop) return
        await new Promise((r) => setTimeout(r, e.delay ?? 60))
        if (e.fail) { o.next({ type: 'RUN_ERROR', message: e.fail }); o.complete(); return }
        o.next(e)
      }
      o.next({ type: 'RUN_FINISHED', threadId: 'pg', runId: 'pg' })
      o.complete()
    })()
    return { unsubscribe: () => { stop = true } }
  } }) }
}
const say = (id, s) => [{ type: 'TEXT_MESSAGE_START', messageId: id, role: 'assistant' },
  ...s.split(/(?<= )/).map((w) => ({ type: 'TEXT_MESSAGE_CONTENT', messageId: id, delta: w, delay: 35 })), { type: 'TEXT_MESSAGE_END', messageId: id }]
async function demoTurn(userText, events, { fresh = true } = {}) {
  if (fresh) chat.reset()
  if (S.opt.mode !== 'inline') chat.open?.()
  chat.agent = scripted(events)
  try { await chat.send(userText) } finally { chat.agent = null }   // the next real message goes to the backend again
}
/** Demos in the chat: what each setting changes, shown at once. */
const DEMOS = {
  conversation: () => demoTurn('Book a haircut tomorrow', [
    ...say('a1', 'Sure. Maria has a free slot tomorrow at 16:30, and Ivan at 10:00. Which one suits you?'),
    { type: 'CUSTOM', name: 'suggestions', value: { items: ['Maria at 16:30', 'Ivan at 10:00', 'Another day'] } }]),
  error: () => demoTurn('Book a haircut tomorrow', [{ fail: 'The booking service did not answer.' }]),
  empty: () => { chat.reset(); if (S.opt.mode !== 'inline') chat.open?.() },
}

// ------------------------------------------------------------------ slot samples (your own components)
const SLOT_CODE = {
  empty: `empty: ({ title, starters }, chat) => {
    const box = document.createElement('div')
    box.className = 'my-welcome'
    box.innerHTML = '<h3>Hi! I can book you in a minute.</h3>'
    for (const s of starters) box.append(Object.assign(document.createElement('button'), { textContent: s, onclick: () => chat.send(s) }))
    return box
  }`,
  user: `user: (text) => Object.assign(document.createElement('div'), { textContent: text, className: 'my-bubble' })`,
  assistant: `assistant: (text) => {
    const box = document.createElement('div')
    box.innerHTML = '<small>Assistant</small>'
    box.append(Object.assign(document.createElement('p'), { textContent: text }))
    return box
  }`,
  header: `header: ({ title, newChat }) => {
    const bar = document.createElement('div')
    bar.innerHTML = '<b>' + title + '</b>'
    bar.append(Object.assign(document.createElement('button'), { textContent: 'New', onclick: newChat }))
    return bar
  }`,
  launcher: `launcher: () => Object.assign(document.createElement('div'), { textContent: 'MB', className: 'my-avatar' })`,
  error: `error: ({ text, retry }) => Object.assign(document.createElement('button'), { textContent: text + ' Tap to retry.', onclick: retry })`,
  suggestions: `suggestions: (items, chat) => {
    const list = document.createElement('div')
    for (const s of items) list.append(Object.assign(document.createElement('button'), { textContent: '→ ' + s, onclick: () => chat.send(s) }))
    return list
  }`,
}
const ICONS = {
  spark: null,
  bubble: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3C6.5 3 2 6.6 2 11c0 2.4 1.3 4.6 3.4 6.1L4.5 21l4.2-2.3c1 .2 2.1.3 3.3.3 5.5 0 10-3.6 10-8s-4.5-8-10-8z"/></svg>',
  scissors: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/></svg>',
  letter: '<svg viewBox="0 0 24 24"><text x="12" y="17" text-anchor="middle" font-size="15" font-weight="700" font-family="-apple-system,sans-serif" fill="currentColor">B</text></svg>',
}
const SLOTS = {
  empty: ({ title, starters }, c) => {
    const box = css(el('div'), 'text-align:center;padding:40px 12px')
    const ico = css(el('div'), 'width:44px;height:44px;margin:0 auto 10px;color:var(--agui-accent)'); ico.innerHTML = ICONS.scissors
    box.append(ico, css(el('h3', {}, `Hi! ${title} can book you in a minute.`), 'margin:0 0 14px;font-size:20px'))
    const list = css(el('div'), 'display:grid;gap:8px')
    for (const s of starters.length ? starters : ['Book a haircut tomorrow', 'What does a beard trim cost?']) {
      list.append(css(el('button', { onclick: () => c.send(s) }, s), 'border:1px solid var(--agui-line-2);background:var(--agui-bg);color:inherit;border-radius:12px;padding:12px;font:inherit;cursor:pointer'))
    }
    box.append(list)
    return box
  },
  user: (t) => css(el('div', {}, t), 'background:var(--agui-accent);color:var(--agui-on-accent);border-radius:18px 18px 4px 18px;padding:10px 14px'),
  assistant: (t) => {
    const box = el('div')
    box.append(css(el('small', {}, 'Assistant'), 'display:block;color:var(--agui-ink-3);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px'))
    box.append(css(el('p', {}, t), 'margin:0'))
    return box
  },
  header: ({ title, newChat }) => css(el('div', {}, css(el('b', {}, title), 'flex:1;font-size:17px'),
    css(el('button', { onclick: newChat }, 'New'), 'border:0;background:var(--agui-soft);color:inherit;border-radius:999px;padding:6px 12px;cursor:pointer')), 'display:flex;align-items:center;gap:8px;width:100%'),
  launcher: () => css(el('div', {}, 'MB'), 'width:100%;height:100%;display:grid;place-items:center;font:700 18px/1 -apple-system,sans-serif;background:linear-gradient(135deg,#ff922b,#e8590c);color:#fff'),
  error: ({ text: t, retry }) => css(el('button', { onclick: retry }, `${t} Tap to retry.`), 'border:1px dashed var(--agui-danger);background:none;color:var(--agui-danger);border-radius:12px;padding:10px 12px;cursor:pointer;font:inherit'),
  suggestions: (items, c) => {
    const list = css(el('div'), 'display:grid;gap:4px')
    for (const s of items) list.append(css(el('button', { onclick: () => c.send(s) }, `→ ${s}`), 'text-align:left;border:0;background:none;color:var(--agui-link);font:inherit;cursor:pointer;padding:4px 0'))
    return list
  },
}
function confirmRenderer(it, ctx) {
  const card = css(el('div'), 'text-align:center;padding:8px 4px')
  const ico = css(el('div'), 'width:34px;height:34px;margin:0 auto;color:var(--agui-accent)')
  ico.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/></svg>'
  card.append(ico, css(el('h3', {}, it.title), 'margin:6px 0 4px;font-size:18px'),
    css(el('p', {}, it.consequence || it.message || ''), 'margin:0 0 12px;color:var(--agui-ink-2)'))
  const yes = css(el('button', { onclick: () => { card.replaceChildren('Booked'); ctx.resolve({ accepted: true }) } }, it.confirm_label || 'Confirm'),
    'border:0;background:var(--agui-accent);color:var(--agui-on-accent);border-radius:999px;padding:12px 24px;font:600 15px/1 inherit;cursor:pointer;width:100%')
  const no = css(el('button', { onclick: () => { card.replaceChildren('Not now'); ctx.resolve({ accepted: false }) } }, 'Not now'),
    'border:0;background:none;color:var(--agui-link);margin-top:6px;font:inherit;cursor:pointer')
  card.append(yes, no)
  return card
}

// ------------------------------------------------------------------ the parts you can style from the page
const PARTS = [
  ['user-bubble', 'Your message bubble'], ['assistant', 'Assistant message'], ['card', 'Every card'], ['card-question', 'Card question'],
  ['chip', 'Chips'], ['option', 'Two-line options'], ['button-primary', 'Main buttons'], ['button-secondary', 'Secondary buttons'],
  ['text-input', 'Text fields'], ['calendar-day-selected', 'Selected day'], ['header', 'Header'], ['composer-box', 'Composer'],
  ['send', 'Send button'], ['fab', 'Launcher'], ['suggestions', 'Quick replies'], ['result', 'Result line ("Filled in")'],
]
function partsCss() {
  return S.parts.map((r) => {
    const d = [r.bg && `background: ${r.bg}`, r.ink && `color: ${r.ink}`, r.border && `border-color: ${r.border}`,
      r.radius !== '' && r.radius != null && `border-radius: ${r.radius}px`, r.weight && `font-weight: ${r.weight}`].filter(Boolean)
    return d.length ? `agui-chat::part(${r.part}) { ${d.join('; ')}; }` : ''
  }).filter(Boolean).join('\n')
}

// ------------------------------------------------------------------ sections

// ------------------------------------------------------------------ the card builder: cards from blocks
// Every block, with the fields it takes. Text fields accept {placeholders}: the model fills them from `data`.
// List fields are edited as lines: "id | label | style" for buttons, "kind | label | value" for links,
// "[x] label" for done steps, "id | label | #hex #hex #hex" for swatches, "a, b, c" for choice options.
const BLOCK_CATALOG = {
  title: { name: 'Title', help: 'the card’s question or heading, with a grey line under it', make: () => ({ type: 'title', text: 'Is this your barber?', subtitle: '' }),
    fields: [['text', 'Text'], ['subtitle', 'Subtitle']] },
  text: { name: 'Text', help: 'a paragraph; **bold** works', make: () => ({ type: 'text', text: 'A short paragraph.' }), fields: [['text', 'Text', 'area'], ['tone', 'Tone', 'tone']] },
  note: { name: 'Note', help: 'a small grey line', make: () => ({ type: 'note', text: 'Free cancellation up to 2 hours before.' }), fields: [['text', 'Text']] },
  row: { name: 'Row', help: 'label and value; rows next to each other form one list', make: () => ({ type: 'row', label: 'Next free slot', value: 'Today, 16:30', icon: 'calendar' }),
    fields: [['label', 'Label'], ['value', 'Value'], ['icon', 'Icon', 'icon'], ['tone', 'Tone', 'tone']] },
  place: { name: 'Place or person', help: 'photo or initial, name, a line, a rating', make: () => ({ type: 'place', title: 'Maria Ivanova', subtitle: 'Barbershop on Arbat', rating: 4.9 }),
    fields: [['title', 'Name'], ['subtitle', 'Line'], ['image', 'Photo URL (https)'], ['rating', 'Rating', 'number']] },
  image: { name: 'Image', help: 'a photo with rounded corners', make: () => ({ type: 'image', src: 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=800', alt: 'Barbershop', ratio: '16:9' }),
    fields: [['src', 'Image URL (https)'], ['alt', 'Description'], ['ratio', 'Shape', 'ratio']] },
  stat: { name: 'Big number', help: 'a balance, a date, a price', make: () => ({ type: 'stat', value: 'Fri, 16:30', label: 'Haircut with Maria', tone: 'ok' }),
    fields: [['value', 'Value'], ['label', 'Label'], ['tone', 'Tone', 'tone']] },
  diff: { name: 'Was → now', help: 'the old value struck through, then the new one', make: () => ({ type: 'diff', label: 'Moved', from: 'Thu, 12:00', to: 'Fri, 16:30' }),
    fields: [['label', 'Label'], ['from', 'Was'], ['to', 'Now']] },
  steps: { name: 'Steps', help: 'a checklist; {left} in the title counts the open steps', make: () => ({ type: 'steps', title: '{left} steps left', items: [{ label: 'Phone number', done: true }, { label: 'Opening hours' }, { label: 'Address' }] }),
    fields: [['title', 'Title'], ['items', 'Steps, one per line, [x] for done', 'steps']] },
  progress: { name: 'Progress', help: 'a thin bar', make: () => ({ type: 'progress', value: 1, max: 3, label: '' }), fields: [['value', 'Value', 'number'], ['max', 'Max', 'number'], ['label', 'Label']] },
  swatches: { name: 'Palettes', help: 'colour sets to pick; the pick comes back in values', make: () => ({ type: 'swatches', name: 'palette', items: [
    { id: 'calm', label: 'Calm', colors: ['#1d1d1f', '#f5f5f7', '#0071e3'] }, { id: 'warm', label: 'Warm', colors: ['#3b2a20', '#fbf3ea', '#e8590c'] }] }),
    fields: [['name', 'Answer name'], ['items', 'One per line: id | label | #hex #hex #hex', 'swatches']] },
  choice: { name: 'Choice', help: 'chips to pick; the pick comes back in values', make: () => ({ type: 'choice', name: 'slot', options: ['16:30', '18:00', '19:30'] }),
    fields: [['name', 'Answer name'], ['options', 'Options, comma separated', 'csv'], ['multiple', 'Several at once', 'bool']] },
  field: { name: 'Field', help: 'an input; its text comes back in values', make: () => ({ type: 'field', name: 'wish', label: 'A wish for the barber', input: 'text', placeholder: 'Shorter on the sides' }),
    fields: [['name', 'Answer name'], ['label', 'Label'], ['input', 'Keyboard', 'input'], ['placeholder', 'Placeholder']] },
  buttons: { name: 'Buttons', help: 'the answers; one primary', make: () => ({ type: 'buttons', items: [{ id: 'yes', label: 'Yes, book her', style: 'primary' }, { id: 'no', label: 'Another barber' }] }),
    fields: [['items', 'One per line: id | label | primary, secondary, plain or danger', 'buttons']] },
  links: { name: 'Links', help: 'act at once: call, route, web, calendar, share, copy, chat', make: () => ({ type: 'links', items: [
    { kind: 'route', label: 'Route to the barbershop', value: 'Arbat 12, Moscow' }, { kind: 'call', label: 'Call the barbershop', value: '+7 495 000 00 00' }] }),
    fields: [['items', 'One per line: kind | label | value', 'links']] },
  divider: { name: 'Divider', help: 'a hairline', make: () => ({ type: 'divider' }), fields: [] },
}
const TEMPLATES = Object.fromEntries(SAMPLES.filter(([, p]) => p.type === 'blocks').map(([n, p]) => [n.replace(/^Blocks: /, ''), p]))
S.builder = { name: 'barber_match', wait: true, blocks: structuredClone(TEMPLATES['your barber?']?.blocks ?? [BLOCK_CATALOG.title.make()]) }
let builderTab = 'yaml'

const lines = {
  steps: [(v) => (v ?? []).map((s) => `${s.done ? '[x] ' : ''}${s.label}`).join('\n'),
    (t) => t.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => (/^\[x\]\s*/i.test(l) ? { label: l.replace(/^\[x\]\s*/i, ''), done: true } : { label: l }))],
  buttons: [(v) => (v ?? []).map((b) => [b.id, b.label, b.style ?? 'secondary'].join(' | ')).join('\n'),
    (t) => t.split('\n').map((l) => l.split('|').map((x) => x.trim())).filter((p) => p[0]).map(([id, label, style]) => ({ id, label: label || id, style: style || 'secondary' }))],
  links: [(v) => (v ?? []).map((b) => [b.kind, b.label, typeof b.value === 'object' ? JSON.stringify(b.value) : b.value].join(' | ')).join('\n'),
    (t) => t.split('\n').map((l) => l.split('|').map((x) => x.trim())).filter((p) => p[0]).map(([kind, label, value]) => {
      let v = value ?? ''
      if (v.startsWith('{')) { try { v = JSON.parse(v) } catch { /* keep the text */ } }
      return { kind, label: label || kind, value: v }
    })],
  swatches: [(v) => (v ?? []).map((s) => [s.id, s.label, (s.colors ?? []).join(' ')].join(' | ')).join('\n'),
    (t) => t.split('\n').map((l) => l.split('|').map((x) => x.trim())).filter((p) => p[0]).map(([id, label, cols]) => ({ id, label: label || id, colors: (cols ?? '').split(/\s+/).filter(Boolean) }))],
  csv: [(v) => (v ?? []).map((o) => (typeof o === 'string' ? o : o.label)).join(', '), (t) => t.split(',').map((x) => x.trim()).filter(Boolean)],
}
const CHOICES = {
  tone: [['', 'Default'], ['accent', 'Accent'], ['ok', 'Success'], ['danger', 'Danger'], ['muted', 'Muted']],
  icon: [['', 'None'], ['calendar', 'Calendar'], ['route', 'Pin'], ['call', 'Phone'], ['web', 'Globe'], ['chat', 'Chat'], ['check', 'Tick']],
  ratio: [['16:9', '16:9'], ['4:3', '4:3'], ['1:1', 'Square']],
  input: [['text', 'Text'], ['tel', 'Phone'], ['email', 'Email'], ['number', 'Number'], ['date', 'Date'], ['url', 'Link']],
}

/** The spec for formguide.yaml: blocks as JSON flow mappings (valid YAML), data from the placeholders used. */
function builderSpec() {
  const used = [...new Set(JSON.stringify(S.builder.blocks).match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g) ?? [])].map((m) => m.slice(1, -1)).filter((n) => n !== 'left')
  const data = used.length ? `{${used.map((n) => `${n}: string`).join(', ')}}` : '{}'
  return ['cards:', `  - type: ${S.builder.name || 'my_card'}`, '    description: Say when the model should show this card.',
    ...(S.builder.wait ? [] : ['    wait: false']), `    data: ${data}   # what the model fills: {name} in the blocks`, '    blocks:',
    ...S.builder.blocks.map((b) => `      - ${JSON.stringify(b)}`)].join('\n')
}
function builderJs() {
  return `// the same card from your own code; the answer is {action, label, values}\nconst answer = await chat.showCard(${JSON.stringify({ type: 'blocks', name: S.builder.name, blocks: S.builder.blocks }, null, 2)})`
}
let previewTimer = 0
function previewCard() {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(() => void showSample({ type: 'blocks', name: S.builder.name, blocks: structuredClone(S.builder.blocks) }, { fresh: true }), 250)
}
function loadIntoBuilder(name, payload) {
  S.builder = { name: payload.name ?? name, wait: true, blocks: structuredClone(payload.blocks) }
  render(); update()
  document.getElementById('builder')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function builderSection() {
  const b = S.builder
  const changed = () => { drawBuilderCode(); previewCard() }
  const templates = el('div', { class: 'chips', style: 'padding:12px 14px' },
    ...Object.entries(TEMPLATES).map(([n, p]) => el('button', { class: 'pill gray', type: 'button', onclick: () => { loadIntoBuilder(n, p); previewCard() } }, n)),
    el('button', { class: 'pill gray', type: 'button', onclick: () => { S.builder = { name: 'my_card', wait: true, blocks: [BLOCK_CATALOG.title.make(), BLOCK_CATALOG.buttons.make()] }; render(); previewCard() } }, 'Empty'))
  const list = el('div', { class: 'blocks-list' })
  b.blocks.forEach((blk, i) => {
    const cat = BLOCK_CATALOG[blk.type] ?? { name: blk.type, fields: [] }
    const move = (d) => { const j = i + d; if (j < 0 || j >= b.blocks.length) return; [b.blocks[i], b.blocks[j]] = [b.blocks[j], b.blocks[i]]; render(); changed() }
    const head = el('div', { class: 'block-head' }, el('b', {}, cat.name), el('span', { class: 'muted' }, ` ${blk.type}`),
      el('span', { class: 'block-tools' },
        el('button', { class: 'icon-x', type: 'button', 'aria-label': 'Move up', disabled: i === 0, onclick: () => move(-1) }, '↑'),
        el('button', { class: 'icon-x', type: 'button', 'aria-label': 'Move down', disabled: i === b.blocks.length - 1, onclick: () => move(1) }, '↓'),
        el('button', { class: 'icon-x', type: 'button', 'aria-label': 'Remove', onclick: () => { b.blocks.splice(i, 1); render(); changed() } }, '×')))
    const fields = cat.fields.map(([key, label, kind]) => {
      let ctl
      if (kind === 'tone' || kind === 'icon' || kind === 'ratio' || kind === 'input') {
        ctl = el('select', { onchange: (e) => { if (e.target.value) blk[key] = e.target.value; else delete blk[key]; changed() } },
          CHOICES[kind].map(([v, l]) => el('option', { value: v, selected: String(blk[key] ?? '') === v }, l)))
      } else if (kind === 'bool') {
        ctl = el('input', { type: 'checkbox', class: 'switch', checked: !!blk[key], onchange: (e) => { blk[key] = e.target.checked; changed() } })
      } else if (lines[kind] || kind === 'area') {
        const [show, read] = lines[kind] ?? [(v) => v ?? '', (t) => t]
        ctl = el('textarea', { rows: kind === 'area' ? 2 : 3, oninput: (e) => { blk[key] = read(e.target.value); changed() } }, show(blk[key]))
      } else {
        ctl = el('input', { type: kind === 'number' ? 'number' : 'text', value: blk[key] ?? '', step: 'any',
          oninput: (e) => { const v = e.target.value; if (v === '') delete blk[key]; else blk[key] = kind === 'number' && !/[{]/.test(v) ? Number(v) : v; changed() } })
      }
      return el('label', { class: 'block-field' }, el('span', { class: 'muted' }, label), ctl)
    })
    list.append(el('div', { class: 'block-card' }, head, el('div', { class: 'help', style: 'margin:0 0 6px' }, cat.help ?? ''), ...fields))
  })
  const addSel = el('select', {}, Object.entries(BLOCK_CATALOG).map(([k, c]) => el('option', { value: k }, c.name)))
  const add = el('div', { class: 'row' }, el('span', { class: 'name' }, 'Add a block'), el('span', { class: 'ctl' }, addSel,
    el('button', { class: 'pill', type: 'button', onclick: () => { b.blocks.push(BLOCK_CATALOG[addSel.value].make()); render(); changed() } }, 'Add')))
  const name = row('Card type', 'snake_case; the model gets a tool show_<type>.', text(() => b.name, (v) => { b.name = v.replace(/[^a-z0-9_]/gi, '_').toLowerCase(); drawBuilderCode() }))
  const wait = choice('Kind', '', [['true', 'Question', 'the turn waits; a button answers the model.'], ['false', 'Display', 'shown while the turn goes on (a route, a receipt); buttons send their label.']],
    () => String(b.wait), (v) => { b.wait = v === 'true'; drawBuilderCode() })
  const codeTabs = seg([['yaml', 'formguide.yaml'], ['js', 'chat.showCard']], () => builderTab, (v) => { builderTab = v; drawBuilderCode() })
  const copy = el('button', { class: 'pill', type: 'button', onclick: async (e) => {
    try { await navigator.clipboard.writeText(document.getElementById('builder-code').textContent); e.target.textContent = 'Copied' } catch { e.target.textContent = 'Select and copy' }
    setTimeout(() => { e.target.textContent = 'Copy' }, 1500)
  } }, 'Copy')
  const code = el('pre', { id: 'builder-code', class: 'builder-code' })
  setTimeout(drawBuilderCode)
  return [
    ...group('Start from', templates),
    ...group('The card', name, wait),
    el('div', { class: 'group-title' }, 'Blocks (top to bottom)'), list, el('div', { class: 'group' }, add,
      el('div', { class: 'row' }, el('span', { class: 'name' }, 'Preview'), el('span', { class: 'ctl' }, el('button', { class: 'pill gray', type: 'button', onclick: () => previewCard() }, 'Show in chat')),
        el('span', { class: 'help' }, 'Every edit redraws it in the preview.'))),
    ...group('The configuration', el('div', { class: 'row wide' }, el('span', { class: 'ctl', style: 'justify-content:space-between' }, codeTabs, copy)), el('div', { style: 'padding:0 14px 14px' }, code)),
  ]
}
function drawBuilderCode() {
  const pre = document.getElementById('builder-code')
  if (pre) pre.textContent = builderTab === 'yaml' ? builderSpec() : builderJs()
}

const sections = [
  ['behaviour', 'Layout and behaviour', 'Where the chat sits and how it talks.', () => [
    ...group('Layout (the mode is switched above the preview)',
      choice('Launcher side', 'Bubble mode only.', [
        ['right', 'Right', 'the bottom right corner, where people look for chat on most sites.'],
        ['left', 'Left', 'the bottom left corner, when the right one is taken (a cookie banner, another widget).']], () => S.opt.bubbleSide, (v) => { S.opt.bubbleSide = v }),
      choice('Opening motion', 'How the bubble opens and closes.', [
        ['spring', 'Spring', 'the window grows out of the launcher with a small overshoot, like iOS. Lively.'],
        ['gentle', 'Gentle', 'the same path without the overshoot, a little quicker. Calm.'],
        ['none', 'None', 'only fades in and out. Also used whenever the device asks for reduced motion.']], () => S.opt.motion, (v) => { S.opt.motion = v }),
      row('Greeting', 'Bubble mode: a speech bubble next to the closed launcher, once per visitor.', text(() => S.opt.greeting, (v) => { S.opt.greeting = v }, 'Need help?'))),
    ...group('Conversation',
      choice('Answer appears', 'How the assistant\'s text shows up while it is being written.', [
        ['words', 'Words', 'typed word by word with a soft fade, easy to read while it streams.'],
        ['plain', 'Plain', 'each piece of text appears the moment it arrives, without animation. Fast and simple.'],
        ['off', 'At once', 'nothing shows until the answer is complete, then all of it. For screen readers or very short answers.']], () => S.opt.typing, (v) => { S.opt.typing = v }),
      row('Tool steps', 'A collapsible list of what the assistant did ("Looked up 3 fields"). Off hides it.', sw(() => S.opt.toolSteps, (v) => { S.opt.toolSteps = v })),
      row('Quick replies', 'Tap-to-send suggestions under each answer and on the empty chat ("What next?").', sw(() => S.opt.quickReplies, (v) => { S.opt.quickReplies = v })),
      row('Microphone', 'Dictate instead of typing.', sw(() => S.opt.mic, (v) => { S.opt.mic = v })),
      choice('Speech recognition', 'Who turns the voice into text.', [
        ['browser', 'Browser', "the browser's own recognition, live as you speak. Works in Chrome and Safari; not in some in-app browsers."],
        ['server', 'Server', 'the chat records, shows a wave and a timer, then sends the recording to your server (POST transcribe, Whisper in the demo). Works everywhere, the text comes after you stop.'],
        ['auto', 'Auto', 'the browser where it works, the server where it does not. Recommended when your server can transcribe.']],
        () => S.opt.dictation, (v) => { S.opt.dictation = v }),
      row('Send when dictation stops', 'Sends right after you stop talking.', sw(() => S.opt.micAutoSend, (v) => { S.opt.micAutoSend = v })),
      row('Attachments', 'The paperclip: send photos and PDFs with a message.', sw(() => S.opt.attach, (v) => { S.opt.attach = v })),
      row('Several files at once', '', sw(() => S.opt.attachMultiple, (v) => { S.opt.attachMultiple = v })),
      row('Largest file', 'Bigger files are refused with a message. Photos are shrunk before this check, so phone pictures usually fit.',
        pick([['20', '20 MB'], ['5', '5 MB'], ['1', '1 MB']], () => S.opt.attachMaxMb, (v) => { S.opt.attachMaxMb = Number(v) }))),
    ...group('Texts',
      row('Title', '', text(() => S.opt.title, (v) => { S.opt.title = v })),
      row('Subtitle', '', text(() => S.opt.subtitle, (v) => { S.opt.subtitle = v })),
      row('Intro', 'The line on the empty chat.', text(() => S.opt.intro, (v) => { S.opt.intro = v }, 'Ask anything about this form.')),
      row('Placeholder', 'Inside the message box.', text(() => S.opt.placeholder, (v) => { S.opt.placeholder = v }, 'Message the assistant…')),
      row('Footnote', 'A line under the message box: a note people should read ("The assistant can make mistakes", "Don\'t type passwords").', text(() => S.opt.footnote, (v) => { S.opt.footnote = v }, 'The assistant can make mistakes.')),
      row('Language', 'All built-in texts; also the dictation language.', pick([['', 'Browser'], ['en', 'English'], ['ru', 'Russian'], ['uk', 'Ukrainian'], ['de', 'German'], ['fr', 'French'], ['it', 'Italian'], ['es', 'Spanish']], () => S.opt.lang, (v) => { S.opt.lang = v }))),
  ]],
  ['colors', 'Colours and theme', 'A theme is a set of colours for light and dark. Pick a preset, then change any colour; your changes become your own theme.', () => {
    const presets = el('div', { class: 'presets' })
    for (const [id, p] of Object.entries(PRESETS)) {
      const l = { ...LIGHT, ...p.light }
      presets.append(el('button', { class: 'preset', type: 'button', 'aria-pressed': String(S.preset === id), onclick: () => {
        S.preset = id; S.light = { ...p.light }; S.dark = { ...p.dark }; render(); update()
      } }, el('span', { class: 'sw' }, ...(p.sw ?? [l.accent, l.soft, l.surface, l.link]).map((c) => css(el('i'), `background:${c}`))), el('b', {}, p.name)))
    }
    const pdesc = el('div', { class: 'help', style: 'padding:0 14px 12px' },
      el('b', {}, PRESETS[S.preset].name), ` — ${PRESETS[S.preset].desc} Pick one, then change any colour below: your changes make your own theme ("my-brand").`)
    const colors = el('div', { class: 'colors' }, el('span', { class: 'c head muted' }, 'Colour'), el('span', { class: 'h head' }, 'Light'), el('span', { class: 'h head' }, 'Dark'))
    for (const [k, name, help] of COLORS) {
      const input = (mode) => el('input', { type: 'color', value: (mode === 'light' ? { ...LIGHT, ...S.light } : { ...DARK, ...S.dark })[k], 'aria-label': `${name}, ${mode}`,
        oninput: (e) => { S[mode][k] = e.target.value; update() } })
      colors.append(el('span', { class: 'c name' }, name, el('small', {}, help)), el('span', { class: 'c' }, input('light')), el('span', { class: 'c' }, input('dark')))
    }
    return [
      ...group('Presets', presets, pdesc),
      ...group('Scheme', choice('Light or dark', '', [
        ['auto', 'Auto', 'follows the device\'s light or dark setting, and switches when it changes. Recommended.'],
        ['light', 'Light', 'always light, whatever the device says.'],
        ['dark', 'Dark', 'always dark.']], () => S.opt.scheme, (v) => { S.opt.scheme = v })),
      ...group('Colours', colors),
    ]
  }],
  ['shape', 'Shape and type', 'Corners, the font and sizes, for everything at once. The ranges are safe: every value looks right.', () => group('',
    row('Cards and the chat frame', 'Field-change and question cards, the inline frame.', ...slider(4, 28, () => S.shape.radius, (v) => { S.shape.radius = v }, 'px', ['card', 'panel'])),
    row('Fields, options and small cells', 'Text and number fields, dropdowns, two-line options, calendar month and year cells, the logo, code blocks.',
      ...slider(2, 20, () => S.shape['radius-sm'], (v) => { S.shape['radius-sm'] = v }, 'px', ['option', 'text-input', 'select', 'number', 'calendar-cell', 'logo'])),
    row('Bubbles and the composer', 'Your message bubble and the message box at the bottom.', ...slider(6, 32, () => S.shape['radius-lg'], (v) => { S.shape['radius-lg'] = v }, 'px', ['user-bubble', 'composer-box'])),
    pillRow(),
    choice('Font', 'For every text in the chat.', [
      ['system', 'System (SF)', 'San Francisco on Apple devices, the device font elsewhere. Native and crisp.'],
      ['rounded', 'SF Rounded', 'softer and friendlier; falls back to the system font outside Apple devices.'],
      ['inter', 'Inter', 'a neutral web font; load it on your page.'],
      ['serif', 'Serif', 'classic and editorial.'],
      ['mono', 'Monospace', 'technical, like code.']], () => S.shape.font, (v) => { S.shape.font = v }, 'pick'),
    row('Drawer width', 'Drawer mode.', ...slider(360, 640, () => S.shape['panel-width'], (v) => { S.shape['panel-width'] = v })),
  )],
  ['components', 'Components', 'Change one kind of element without touching the rest. Each value overrides the colours above for that component only.', () => {
    // [min, max] per size token: safe ranges only (padding never 0, a field never too short to tap)
    const RANGE = { 'card-radius': [4, 28], 'card-padding': [10, 24], 'bubble-radius': [6, 28], 'chip-radius': [4, 24], 'option-radius': [4, 20],
      'button-radius': [6, 24], 'input-radius': [4, 20], 'input-height': [40, 56], 'composer-radius': [8, 32] }
    const PARTS_OF = { 'card-bg': ['card'], 'card-border': ['card'], 'card-radius': ['card'], 'card-padding': ['card'], 'bubble-user-bg': ['user-bubble'],
      'bubble-user-ink': ['user-bubble'], 'bubble-radius': ['user-bubble'], 'chip-bg': ['chip'], 'chip-ink': ['chip'], 'chip-on-bg': ['chip'], 'chip-radius': ['chip'],
      'option-radius': ['option'], 'button-bg': ['button-primary'], 'button-ink': ['button-primary'], 'button-radius': ['button'], 'input-bg': ['text-input'],
      'input-radius': ['text-input'], 'input-height': ['text-input'], 'composer-bg': ['composer-box'], 'composer-radius': ['composer-box'], 'header-bg': ['header'],
      'calendar-on-bg': ['calendar-day-selected'] }
    const tok = (key, name, kind = 'color', base = '') => {
      if (kind === 'color') {
        const on = el('input', { type: 'checkbox', class: 'switch', checked: key in S.comp, 'aria-label': `Custom ${name}`, onchange: (e) => { if (e.target.checked) S.comp[key] = color.value; else delete S.comp[key]; update(); flash(PARTS_OF[key]) } })
        const color = el('input', { type: 'color', value: S.comp[key] || base, oninput: (e) => { S.comp[key] = e.target.value; on.checked = true; update(); flash(PARTS_OF[key]) } })
        return row(name, '', color, on)
      }
      const [min, max] = RANGE[key] ?? [0, 32]
      const cur = Math.min(max, Math.max(min, parseInt(S.comp[key] ?? base, 10)))
      return row(name, '', ...slider(min, max, () => cur, (v) => { S.comp[key] = `${v}px` }, 'px', PARTS_OF[key]))
    }
    return [
      ...group('Cards', tok('card-bg', 'Background', 'color', LIGHT.surface), tok('card-border', 'Border', 'color', LIGHT.line), tok('card-radius', 'Corners', 'px', 14), tok('card-padding', 'Padding', 'px', 14),
        choice('Frosted glass', 'Blurs what is behind the card; pair it with a translucent background (the Glass and Bold themes do).', [
          ['', 'None', 'a solid card.'],
          ['blur(16px) saturate(160%)', 'Soft', 'a light frost, like a widget on the iOS home screen.'],
          ['blur(28px) saturate(180%)', 'Strong', 'a deep frost, like Control Center.']],
          () => S.comp['card-blur'] ?? '', (v) => { if (v) S.comp['card-blur'] = v; else delete S.comp['card-blur']; setTimeout(() => flash(['card'])) })),
      ...group('Your messages', tok('bubble-user-bg', 'Bubble', 'color', LIGHT.soft), tok('bubble-user-ink', 'Text', 'color', LIGHT.ink), tok('bubble-radius', 'Corners', 'px', 20)),
      ...group('Chips and options', tok('chip-bg', 'Chip background', 'color', LIGHT.bg), tok('chip-ink', 'Chip text', 'color', LIGHT['ink-2']), tok('chip-on-bg', 'Selected chip', 'color', LIGHT.accent),
        tok('chip-radius', 'Chip corners', 'px', 20), tok('option-radius', 'Option corners', 'px', 10)),
      ...group('Buttons', tok('button-bg', 'Main button', 'color', LIGHT.accent), tok('button-ink', 'Main button text', 'color', LIGHT['on-accent']), tok('button-radius', 'Corners', 'px', 20)),
      ...group('Inputs and composer', tok('input-bg', 'Field fill', 'color', LIGHT.soft), tok('input-radius', 'Field corners', 'px', 10), tok('input-height', 'Field height', 'px', 44),
        tok('composer-bg', 'Composer', 'color', LIGHT.bg), tok('composer-radius', 'Composer corners', 'px', 20)),
      ...group('Header and calendar', tok('header-bg', 'Header', 'color', LIGHT.bg), tok('calendar-on-bg', 'Selected day', 'color', LIGHT.accent)),
    ]
  }],
  ['parts', 'Style any element', 'Every element has a part name. Add a rule for any of them: this is plain CSS on your page, agui-chat::part(name).', () => {
    const list = el('div', { class: 'group' })
    S.parts.forEach((r, i) => {
      const color = (k, label) => el('input', { type: 'color', value: r[k] || '#888888', title: label, 'aria-label': label, oninput: (e) => { r[k] = e.target.value; update(); flash([r.part]) } })
      list.append(el('div', { class: 'row wide' }, el('span', { class: 'name' }, PARTS.find(([p]) => p === r.part)?.[1] ?? r.part, ' ', el('code', { class: 'muted' }, `::part(${r.part})`)),
        el('span', { class: 'ctl' }, color('bg', 'Background'), color('ink', 'Text'), color('border', 'Border'),
          el('input', { type: 'number', min: 0, max: 40, value: r.radius ?? '', placeholder: 'radius', style: 'width:84px', oninput: (e) => { r.radius = e.target.value; update() } }),
          pick([['', 'weight'], ['400', 'Regular'], ['600', 'Semibold'], ['700', 'Bold']], () => r.weight ?? '', (v) => { r.weight = v }),
          el('button', { class: 'pill gray', type: 'button', onclick: () => { S.parts.splice(i, 1); render(); update() } }, 'Remove'))))
    })
    const sel = el('select', {}, PARTS.map(([p, n]) => el('option', { value: p }, n)))
    const add = el('div', { class: 'row' }, el('span', { class: 'name' }, 'Add a rule for'), el('span', { class: 'ctl' }, sel,
      el('button', { class: 'pill', type: 'button', onclick: () => { S.parts.push({ part: sel.value }); render(); update(); flash([sel.value]) } }, 'Add')),
      el('span', { class: 'help' }, 'The full list of names is on the Themes page of the docs (Parts).'))
    return [S.parts.length ? list : null, el('div', { class: 'group' }, add)]
  }],
  ['cards', 'Cards', 'What the assistant may show, and what each card offers. Try every card in the preview.', () => {
    const ex = (id, name, help) => row(name, help, sw(() => !S.cards.exclude.includes(id), (on) => {
      S.cards.exclude = on ? S.cards.exclude.filter((x) => x !== id) : [...S.cards.exclude, id]
    }))
    // every switch here redraws its card in the preview, so the change is visible at once
    const fieldDemo = () => void showSample(sample('Field changes'), { fresh: true })
    const flag = (k, name, help) => row(name, help, sw(() => S.cards[k], (v) => { S.cards[k] = v; setTimeout(fieldDemo) }))
    const showBtn = (name) => el('button', { class: 'pill gray small', type: 'button', onclick: () => void showSample(sample(name), { fresh: true }) }, 'Show')
    const ex2 = (id, name, help, demo) => {
      const r = ex(id, name, help)
      r.querySelector('.ctl').prepend(showBtn(demo))
      return r
    }
    return [
      ...group('Field-change card ("Fill in these fields?")',
        row('The card', 'Each switch below redraws it in the preview. Undo appears after you tap Fill in.', showBtn('Field changes')),
        flag('select', 'Tick rows', 'The checkbox on the left of each row: fill in only some of them.'),
        flag('diff', 'Old → new', 'When a field already had a value, the old one is shown struck through above the new one (in the sample: the Date, 18 → 20 November). Off: only the new value.'),
        flag('reason', 'Reason', 'The grey line under the value: why the assistant proposes it ("From your message").'),
        flag('edit', 'Edit', 'The Edit link on each row: change the value before filling it in.'),
        flag('jump', 'Show', 'The Show link on each row: scroll to the field in your form.'),
        flag('undo', 'Undo', 'After Fill in, the card folds into "Filled in 2 fields" with Undo next to it.'),
        row('Undo stays for', 'How long Undo is offered after a card is applied.', ...slider(5, 60, () => S.cards.undoSeconds, (v) => { S.cards.undoSeconds = v }, ' s'))),
      ...group('Cards the assistant may use',
        row('', 'Off: the assistant asks in plain text instead. Show draws the card anyway, so you can see what it is.'),
        ex2('ask', 'Questions', 'Options, days, slots, several fields.', 'Options with details'),
        ex2('ask.compare', 'Comparisons', 'Two or three options side by side.', 'Comparison'),
        ex2('ask.range', 'Steppers and sliders', 'Numbers in a range.', 'Stepper'),
        ex2('ask.multi', 'Several fields at once', 'Contacts and the like in one card.', 'Several fields'),
        ex2('upload', 'File requests', 'Asks for a photo or a document.', 'File request'),
        ex2('confirm', 'Confirmations', 'Before sending or cancelling.', 'Confirmation'),
        ex2('review', 'Form review', 'Status and the check before sending.', 'Check before sending')),
      ...group('Steps', flag('cardSteps', 'Show card steps', '"Preparing a question" as a step, although the card follows.')),
    ]
  }],
  ['builder', 'Your own cards', 'Compose a card from blocks: add, edit, reorder. The preview shows it live in your theme; the code below is the card spec for formguide.yaml (the model fills the {placeholders}) and the same card for chat.showCard().', () => builderSection()],
  ['replace', 'Replace components', 'Put your own component in place of any piece, or replace a whole card. Your function returns an element; return nothing to keep ours.', () => {
    // turning a piece on (or off) shows it in the preview at once
    const DEMO_OF = { empty: DEMOS.empty, user: DEMOS.conversation, assistant: DEMOS.conversation, suggestions: DEMOS.conversation, error: DEMOS.error,
      header: () => flash(['header']), launcher: () => { if (S.opt.mode !== 'bubble') setMode('bubble') }, confirmCard: () => void showSample(sample('Confirmation'), { fresh: true }) }
    const slot = (k, name, help) => row(name, help, sw(() => S.slots[k], (v) => { S.slots[k] = v; setTimeout(() => DEMO_OF[k]?.()) }))
    return [
      ...group('Pieces of the chat (options.render)',
        row('', 'Each switch shows its piece in the preview: a short scripted conversation, an error, the empty chat or the launcher.'),
        slot('empty', 'Empty chat', 'Your own welcome screen with the starters.'),
        slot('user', 'Your messages', 'Your own bubble.'),
        slot('assistant', 'Answers', 'Wrap or replace every finished answer.'),
        slot('header', 'Header', 'Your own top bar.'),
        slot('suggestions', 'Quick replies', 'Your own list instead of chips.'),
        slot('error', 'Errors', 'Your own failure message with retry.'),
        slot('launcher', 'Launcher', 'Bubble mode: an avatar instead of the icon.')),
      ...group('Whole cards (chat.renderers)', slot('confirmCard', 'Confirmation card', 'A custom confirm card (try "Confirmation" in Cards).')),
      ...group('Icons', choice('Logo', 'In the header and on the launcher (options.icons). Any SVG of yours works too.', [
        ['spark', 'Spark', 'the default assistant mark.'],
        ['bubble', 'Bubble', 'a speech bubble: "chat" at a glance.'],
        ['scissors', 'Scissors', 'an example of a brand icon (the barbershop).'],
        ['letter', 'Letter', 'a monogram of the brand.']], () => S.icon, (v) => { S.icon = v; setTimeout(() => flash(['logo', 'fab'])) })),
    ]
  }],
]

function render() {
  const toc = document.getElementById('toc'), box = document.getElementById('sections')
  toc.replaceChildren(...sections.map(([id, title]) => el('a', { href: `#${id}` }, title)))
  box.replaceChildren(...sections.map(([id, title, lead, body]) => el('section', { class: 'sec', id }, el('h2', {}, title), el('p', {}, lead), ...[body()].flat())))
}

// ------------------------------------------------------------------ the chat and the backend
let form = null
async function load() {
  try {
    const f = await (await fetch(`/java/form?form_id=${FORM_ID}`)).json()
    const r = await (await fetch('/agent/layouts', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsx: f.jsx, form_id: f.form_id, domain: f.domain, config: f.config }) })).json()
    form = { jsx_hash: r.jsx_hash, config: f.config }
  } catch { form = { jsx_hash: 'offline', config: { props: {}, state: {} } } }   // showCard still works
}
async function apply(changes) {
  try {
    form.config = await (await fetch('/java/event', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form_id: FORM_ID, state: form.config.state, changes }) })).json()
  } catch { Object.assign(form.config.state, changes) }
  return form.config
}
const cardFlags = () => ({ select: S.cards.select, diff: S.cards.diff, reason: S.cards.reason, edit: S.cards.edit, jump: S.cards.jump, undo: S.cards.undo })
function plugin() {
  return AguiChat.formguide({ getState: () => ({ ...form, form_id: FORM_ID, ui: { now: new Date().toString() } }), applyChanges: apply,
    fieldCard: cardFlags(), undoSeconds: S.cards.undoSeconds, cardSteps: S.cards.cardSteps, exclude: S.cards.exclude })
}

const themed = () => S.preset !== 'default' || Object.keys(S.light).length || Object.keys(S.dark).length || Object.keys(S.comp).length
  || S.shape.radius !== 14 || S.shape['radius-sm'] !== 10 || S.shape['radius-lg'] !== 20 || S.shape['radius-pill'] !== 999 || S.shape.font !== 'system' || S.shape['panel-width'] !== 460
function themeObject() {
  const t = {}
  if (PRESETS[S.preset]?.base) t.extends = PRESETS[S.preset].base
  const tokens = { ...S.comp }
  if (S.shape.radius !== 14) tokens.radius = `${S.shape.radius}px`
  if (S.shape['radius-sm'] !== 10) tokens['radius-sm'] = `${S.shape['radius-sm']}px`
  if (S.shape['radius-lg'] !== 20) tokens['radius-lg'] = `${S.shape['radius-lg']}px`
  if (S.shape['radius-pill'] !== 999) tokens['radius-pill'] = `${S.shape['radius-pill']}px`
  if (S.shape['panel-width'] !== 460) tokens['panel-width'] = `${S.shape['panel-width']}px`
  if (S.shape.font !== 'system') tokens.font = FONTS[S.shape.font]
  if (Object.keys(tokens).length) t.tokens = tokens
  const diff = (cur, base) => Object.fromEntries(Object.entries(cur).filter(([k, v]) => v && v.toLowerCase() !== base[k]))
  const l = diff(S.light, LIGHT), d = diff(S.dark, DARK)
  if (Object.keys(l).length) t.light = l
  if (Object.keys(d).length) t.dark = d
  return t
}
const changedOptions = () => {
  const base = { mode: 'floating', scheme: 'auto', lang: '', typing: 'words', toolSteps: true, quickReplies: true, mic: true, micAutoSend: false, dictation: 'browser', attach: true,
    attachMultiple: true, attachMaxMb: 20, bubbleSide: 'right', greeting: '', motion: 'spring', title: '', subtitle: '', intro: '', placeholder: '', footnote: '' }
  return Object.fromEntries(Object.entries(S.opt).filter(([k, v]) => v !== base[k]))
}
const renderSlots = () => {
  const out = {}
  for (const [k, on] of Object.entries(S.slots)) if (on && SLOTS[k]) out[k] = SLOTS[k]
  return out
}

let lastPlugin = ''
function update() {
  // the theme
  // a built-in theme pack loads on first use; my-brand extends it, so define it once the pack is there
  const base = PRESETS[S.preset]?.base
  const waiting = base && !AguiChat.themes().includes(base)
  if (waiting) void AguiChat.loadTheme(base).then(() => update())
  if (themed() && !waiting) AguiChat.defineTheme('my-brand', themeObject())
  // the chat's options (attributes in the HTML code)
  const opts = { ...S.opt, theme: waiting ? base : themed() ? 'my-brand' : 'default', render: renderSlots(), icons: ICONS[S.icon] ? { logo: ICONS[S.icon] } : {} }
  if (opts.scheme === 'auto') opts.scheme = ''
  chat.options = opts
  // the plugin: rebuilt when card options change
  const key = JSON.stringify(S.cards)
  if (form && key !== lastPlugin) { lastPlugin = key; chat.plugins = [plugin()] }
  // replaced cards
  if (S.slots.confirmCard) chat.renderers.set('confirm', confirmRenderer)
  else if (chat.renderers.get('confirm') === confirmRenderer && form) chat.plugins = [plugin()]
  // page CSS for parts
  let style = document.getElementById('pg-parts')
  if (!style) { style = el('style', { id: 'pg-parts' }); document.head.append(style) }
  style.textContent = partsCss()
  // where the chat is
  const host = document.getElementById('inline-host')
  const inline = S.opt.mode === 'inline' || S.opt.mode === 'hero'   // hero also sits in the page
  document.getElementById('inline-host').classList.toggle('hero', S.opt.mode === 'hero')
  if (inline && chat.parentElement !== host) host.append(chat)
  if (!inline && chat.parentElement === host) document.body.append(chat)
  document.getElementById('corner-note').hidden = inline
  // only page mode covers the settings: then a floating bar leads back; otherwise the toolbar above the preview does
  document.getElementById('floatbar').hidden = S.opt.mode !== 'page'
  document.querySelectorAll('#quick-mode button, #pv-mode button').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.v === S.opt.mode)))
  document.getElementById('pv-mode-help').textContent = MODE_HELP[S.opt.mode]
  document.getElementById('corner-note').textContent = S.opt.mode === 'page' ? 'Page mode covers the whole window. Switch back to Inline to keep editing.'
    : `The chat lives in the corner of the page in this mode. Tap the launcher at the bottom ${S.opt.bubbleSide === 'left' && S.opt.mode === 'bubble' ? 'left' : 'right'}.`
  drawCode()
}

// ------------------------------------------------------------------ the code to copy: live, next to the preview, your changes marked
let tab = 'html'
const q = (v) => JSON.stringify(v)
const attr = (k) => k.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`)
const indent = (s, n) => s.replace(/\n/g, `\n${' '.repeat(n)}`)
function pluginLines() {
  const o = [`  getState: () => ({ config, jsx_hash, form_id }),   // your form as your backend last built it`,
    `  applyChanges: (changes) => yourBackend.apply(changes),`]
  const flags = cardFlags()
  if (Object.values(flags).some((v) => !v)) o.push(`  fieldCard: ${JSON.stringify(flags).replace(/,/g, ', ')},`)
  if (S.cards.undoSeconds !== 20) o.push(`  undoSeconds: ${S.cards.undoSeconds},`)
  if (S.cards.cardSteps) o.push(`  cardSteps: true,`)
  if (S.cards.exclude.length) o.push(`  exclude: ${JSON.stringify(S.cards.exclude)},   // cards the assistant may not use`)
  return o
}
const themeCode = (fn) => `${fn}('my-brand', ${JSON.stringify(themeObject(), null, 2)})`
const CONFIRM_CODE = `(card, ctx) => {
  const box = document.createElement('div')
  // ... card.title, card.details, card.confirm_label
  // yes: ctx.resolve({ accepted: true }), no: ctx.resolve({ accepted: false })
  return box
}`
function code() {
  const opts = changedOptions()
  const slots = Object.entries(S.slots).filter(([k, on]) => on && SLOT_CODE[k]).map(([k]) => SLOT_CODE[k])
  const icon = ICONS[S.icon]
  const cssText = partsCss()

  // HTML: one file, everything in it
  const attrs = Object.entries(opts).map(([k, v]) => (v === true ? attr(k) : v === false ? `${attr(k)}="off"` : `${attr(k)}=${q(String(v))}`))
  if (themed()) attrs.push('theme="my-brand"')
  const js = [`const chat = document.getElementById('chat')`]
  if (themed()) js.push(`\n// your theme: colours for light and dark, shape and component tokens\n${themeCode('AguiChat.defineTheme')}`)
  js.push(`\n// the form: what the chat reads and how accepted values reach your form\nchat.use(AguiChat.formguide({\n${pluginLines().join('\n')}\n}))`)
  const extra = []
  if (slots.length) extra.push(`  render: {\n    ${slots.map((s) => indent(s, 4)).join(',\n    ')},\n  },`)
  if (icon) extra.push(`  icons: { logo: ${q(icon)} },`)
  if (extra.length) js.push(`\n// your own components and icons\nchat.options = {\n${extra.join('\n')}\n}`)
  if (S.slots.confirmCard) js.push(`\n// a whole card of your own: draw it, call ctx.resolve(answer)\nchat.renderers.set('confirm', ${CONFIRM_CODE})`)
  const html = [`<!-- the widget: dist/agui-chat.iife.js from @formguide/agui-chat, served by your app -->\n<script src="/agui-chat.iife.js"></script>`, '',
    `<agui-chat\n  id="chat"\n  url="/agent/run"${attrs.map((a) => `\n  ${a}`).join('')}\n></agui-chat>`, '',
    `<script>\n${js.join('\n')}\n</script>`, ...(cssText ? ['', `<style>\n${cssText}\n</style>`] : [])].join('\n')

  // React: the same, as a component
  const props = Object.entries(opts).map(([k, v]) => (v === true ? k : typeof v === 'string' ? `${k}=${q(v)}` : `${k}={${q(v)}}`))
  if (themed()) props.push('theme="my-brand"')
  props.push('plugins={plugins}')
  if (slots.length) props.push(`render={render}`)
  if (icon) props.push(`icons={{ logo: ${q(icon)} }}`)
  if (S.slots.confirmCard) props.push('renderers={{ confirm: confirmCard }}')
  const react = [`import { AguiChat } from '@formguide/agui-chat/react'`,
    `import { formguide } from '@formguide/agui-chat/formguide'`,
    ...(themed() ? [`import { defineTheme } from '@formguide/agui-chat'`] : []), '',
    ...(themed() ? [`// your theme: once, outside the component\n${themeCode('defineTheme')}`, ''] : []),
    `// the form: what the chat reads and how accepted values reach your form\nconst plugins = [formguide({\n${pluginLines().join('\n')}\n})]`, '',
    ...(slots.length ? [`// your own components\nconst render = {\n  ${slots.map((s) => indent(s, 2)).join(',\n  ')},\n}`, ''] : []),
    ...(S.slots.confirmCard ? [`// a whole card of your own\nconst confirmCard = ${CONFIRM_CODE}`, ''] : []),
    `export function Chat() {\n  return (\n    <AguiChat\n      url="/agent/run"${props.map((p) => `\n      ${p}`).join('')}\n    />\n  )\n}`,
    ...(cssText ? ['', `/* in your CSS file */\n${cssText}`] : [])].join('\n')

  // Theme: only the look, to share with a designer or reuse in several apps
  const theme = themed() ? `${themeCode('AguiChat.defineTheme')}${cssText ? `\n\n/* page CSS */\n${cssText}` : ''}`
    : `// The default theme: nothing to add.\n// Change a colour, a corner or a font on the left and your theme appears here.`
  return { html, react, theme }
}

// the code of the untouched playground: lines that differ from it are your changes
let BASE = null
function drawCode() {
  const all = code()
  BASE ??= structuredClone(all)
  const base = new Set(BASE[tab].split('\n'))
  const pre = document.getElementById('code')
  const lines = all[tab].split('\n')
  const mine = lines.filter((l) => l.trim() && !base.has(l)).length
  pre.replaceChildren(...lines.map((l) => el('span', { class: l.trim() && !base.has(l) ? 'ln mine' : 'ln' }, `${l}\n`)))
  const n = changesCount()
  document.getElementById('code-count').textContent = n ? String(n) : ''
  document.getElementById('code-count').hidden = !n
  document.getElementById('code-note').textContent = mine ? `${mine} highlighted line${mine > 1 ? 's' : ''}: your changes.` : 'Nothing changed yet: change anything on the left and it appears here, highlighted.'
}
/** How many settings differ from the start. */
function changesCount() {
  const walk = (a, b) => {
    if (a && typeof a === 'object' && b && typeof b === 'object') {
      const keys = new Set([...Object.keys(a), ...Object.keys(b)])
      let n = 0
      for (const k of keys) n += walk(a[k], b[k])
      return n
    }
    return JSON.stringify(a) === JSON.stringify(b) ? 0 : 1
  }
  return walk(S, S0)
}
document.getElementById('code-tabs').addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b) return
  tab = b.dataset.tab
  document.querySelectorAll('#code-tabs button').forEach((x) => x.setAttribute('aria-selected', String(x === b)))
  drawCode()
})
document.getElementById('copy').addEventListener('click', async (e) => {
  const b = e.currentTarget
  try { await navigator.clipboard.writeText(code()[tab]); b.textContent = 'Copied' } catch { b.textContent = 'Select and copy' }
  setTimeout(() => { b.textContent = 'Copy' }, 1500)
})
// Chat or Code in the preview column
function setView(v) {
  document.querySelectorAll('#view button').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.v === v)))
  document.getElementById('codeview').hidden = v !== 'code'
  document.getElementById('chatview').hidden = v !== 'chat'
  if (v === 'code') drawCode()
}
document.getElementById('view').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setView(b.dataset.v) })
document.getElementById('width').addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b) return
  document.querySelectorAll('#width button').forEach((x) => x.setAttribute('aria-checked', String(x === b)))
  document.getElementById('frame').classList.toggle('phone', b.dataset.w === '390')
})

// ------------------------------------------------------------------ the way back from bubble, drawer and page modes
function setMode(m) {
  S.opt.mode = m; render(); update()
  if (m === 'hero') { chat.close?.(); chat.reset() }   // the field alone, as a visitor first sees it
  else if (m !== 'inline') chat.open?.()
}
document.getElementById('back').addEventListener('click', () => setMode('inline'))
for (const id of ['quick-mode', 'pv-mode']) document.getElementById(id).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setMode(b.dataset.v) })
const MODE_HELP = {
  bubble: 'Bubble: a round button in the corner grows a compact chat window. The page stays usable.',
  floating: 'Drawer: a full-height panel from the side, the page dimmed behind it.',
  inline: 'Inline: the chat sits inside your page like any other block, as here.',
  page: 'Page: the chat takes the whole window.',
  hero: 'Hero: a landing\'s big field; the first message grows it into the chat (a full-screen sheet on a phone).',
}
// every card and piece, one tap away: shown in the preview without the agent
document.getElementById('try').append(
  ...SAMPLES.filter(([, p]) => p.type !== 'blocks').map(([name, p]) => el('button', { class: 'pill gray', type: 'button', onclick: () => void showSample(p) }, name)),
  // cards composed from blocks are custom: a tap shows one and opens how it is configured
  el('span', { class: 'try-label' }, 'Custom, from blocks'),
  ...SAMPLES.filter(([, p]) => p.type === 'blocks').map(([name, p]) => el('button', { class: 'pill gray custom', type: 'button',
    title: 'A custom card: shows it and opens its configuration in Your own cards',
    onclick: () => { loadIntoBuilder(name, p); void showSample(p, { fresh: true }) } }, el('span', { class: 'tag' }, 'Custom'), name.replace(/^Blocks: /, ''))),
  el('button', { class: 'pill gray', type: 'button', onclick: () => void DEMOS.conversation() }, 'Conversation'),
  el('button', { class: 'pill gray', type: 'button', onclick: () => void DEMOS.error() }, 'Error'),
  el('button', { class: 'pill gray', type: 'button', onclick: () => { DEMOS.empty(); document.getElementById('answer').hidden = true } }, 'Clear'))
document.getElementById('answer-x').addEventListener('click', () => { document.getElementById('answer').hidden = true })
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && S.opt.mode === 'page') setMode('inline') })   // the chat's own Esc closes bubble and drawer

// ------------------------------------------------------------------ start
render()
load().then(() => {
  lastPlugin = JSON.stringify(S.cards)
  chat.plugins = [plugin()]
  chat.registerTool({
    name: 'get_user_locale', description: "The user's browser language and time zone.",
    parameters: { type: 'object', properties: {} },
    handler: () => ({ language: navigator.language, time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone }),
  })
  update()
})
update()

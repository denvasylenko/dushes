/**
 * Cards from blocks: small parts (a title, a row, a place, a palette, buttons…) that compose any card and always
 * look like the chat's own. The developer lays a card out (on the server, in formguide.yaml `cards:`, or with
 * `chat.showCard({ type: 'blocks', blocks })`); the model only fills the data. Colours come from the theme and a
 * block's `tone`, never from the card, so every card follows the theme, light and dark.
 *
 *   { type: 'blocks', blocks: [
 *     { type: 'place', title: 'Maria', subtitle: 'Arbat 12', image: 'https://…', rating: 4.9 },
 *     { type: 'buttons', items: [{ id: 'yes', label: 'Yes, book her', style: 'primary' }, { id: 'no', label: 'Another barber' }] },
 *   ] }
 *
 * A button with an `id` answers {action, label, values} (values: the card's choice, swatches and field values by
 * name) and folds the card into its result line. Links (call, route, web, calendar, share, copy, chat) act at once.
 * A display card (`wait: false`, from a `CUSTOM card` event) has nobody waiting: its buttons send their label.
 */
import { h, mdInline } from '../dom'
import type { Interrupt, RendererContext } from '../types'

export type Tone = 'accent' | 'ok' | 'danger' | 'muted'
/** A button's answer: its id, its label, the card's values, and the button itself (its `fills`). */
type Answer = (action: string, label: string, values: Record<string, unknown>, button: Record<string, unknown>) => void
export interface Block { type: string; [k: string]: unknown }
type Item = Record<string, unknown>

const str = (v: unknown): string => (v == null ? '' : String(v))
const list = (v: unknown): Item[] => (Array.isArray(v) ? v.filter((x) => x && typeof x === 'object') as Item[] : [])
/** Options and swatches: objects, or plain strings from data (a list of slots: "16:30" -> {id, label}). */
const options = (v: unknown): Item[] => (Array.isArray(v) ? v.map((x) => (typeof x === 'string' || typeof x === 'number' ? { id: String(x), label: String(x) } : x))
  .filter((x) => x && typeof x === 'object') as Item[] : [])
const tone = (t: unknown): string => (['accent', 'ok', 'danger', 'muted'].includes(str(t)) ? ` tone-${t}` : '')
/** Only web and inline images from data: no javascript:, no file: */
const safeUrl = (u: unknown, img = false): string => {
  const s = str(u).trim()
  return /^https?:\/\//i.test(s) || (img && /^data:image\//i.test(s)) ? s : ''
}
const md = (s: unknown, cls: string): HTMLElement => { const e = h('div', { class: cls }); e.innerHTML = mdInline(str(s)); return e }

// line icons in the SF Symbols spirit: 24 grid, 1.8 stroke, round caps
const ICON: Record<string, string> = {
  call: 'M5 4h3l2 5-2.5 1.5a11 11 0 0 0 6 6L15 14l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2',
  route: 'M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12zM12 11.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5',
  web: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3',
  calendar: 'M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM4 10h16M8 3v4M16 3v4',
  share: 'M12 15V3M8 7l4-4 4 4M6 11H5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-1',
  copy: 'M9 9h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V10a1 1 0 0 1 1-1zM5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1',
  chat: 'M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-5 4V6a1 1 0 0 1 1-1z',
  check: 'M5 12.5l4.5 4.5L19 7',
}
const icon = (name: string): HTMLElement => {
  const s = h('span', { class: 'bk-ico', 'aria-hidden': 'true' })
  if (ICON[name]) s.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${ICON[name]}"/></svg>`
  return s
}

/** An .ics file for "Add to calendar": {title, start: ISO, minutes?, place?}. */
function ics(v: Item): string {
  const start = new Date(str(v.start))
  if (Number.isNaN(start.getTime())) return ''
  const end = new Date(start.getTime() + (Number(v.minutes) || 60) * 60000)
  const f = (d: Date) => d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
  const esc = (s: unknown) => str(s).replace(/[\\;,]/g, (m) => `\\${m}`).replace(/\n/g, '\\n')
  return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'BEGIN:VEVENT', `DTSTART:${f(start)}`, `DTEND:${f(end)}`,
    `SUMMARY:${esc(v.title)}`, ...(v.place ? [`LOCATION:${esc(v.place)}`] : []), 'END:VEVENT', 'END:VCALENDAR'].join('\r\n')
}

/** What a link does: open, call, route, add to calendar, share, copy or send as a message. */
function linkEl(it: Item, c: RendererContext): HTMLElement {
  const kind = str(it.kind) || 'web'
  const label = str(it.label)
  const value = it.value
  let href = ''
  if (kind === 'call') href = `tel:${str(value).replace(/[^\d+]/g, '')}`
  else if (kind === 'route') href = `https://maps.apple.com/?q=${encodeURIComponent(str(value))}`
  else if (kind === 'web') href = safeUrl(value)
  else if (kind === 'calendar' && value && typeof value === 'object') {
    const data = ics(value as Item)
    if (data) href = `data:text/calendar;charset=utf-8,${encodeURIComponent(data)}`
  }
  const body = [icon(kind), h('span', null, label)]
  if (href) {
    return h('a', { class: 'bk-link', part: 'block-link', href, target: kind === 'web' || kind === 'route' ? '_blank' : null,
      rel: 'noopener noreferrer', download: kind === 'calendar' ? `${label || 'event'}.ics` : null }, ...body)
  }
  const done = (b: HTMLElement) => { b.classList.add('done'); b.querySelector('span:last-child')!.textContent = c.t('copied'); setTimeout(() => { b.classList.remove('done'); b.querySelector('span:last-child')!.textContent = label }, 1500) }
  const b = h('button', { class: 'bk-link', part: 'block-link', type: 'button', onclick: async () => {
    if (kind === 'chat') return void c.chat.send(str(value) || label)
    const text = str(value)
    if (kind === 'share' && navigator.share) { try { await navigator.share({ text, ...(safeUrl(value) ? { url: text } : {}) }) } catch { /* closed */ } return }
    try { await navigator.clipboard.writeText(text); done(b) } catch { /* no clipboard */ }
  } }, ...body) as HTMLElement
  return b
}

/**
 * A blocks card. `answer(action, label, values)` is called by a button with an id; null for a display card
 * (its buttons send their label as a message instead).
 */
/** A host's own handling of a button: resolves true when handled (the chat then does nothing more). */
export type OnAction = (id: string, label: string, values: Record<string, unknown>) => Promise<boolean>

export function blocksCard(it: Interrupt | Record<string, unknown>, c: RendererContext, answer: Answer | null, onAction?: OnAction): HTMLElement {
  const values: Record<string, unknown> = {}
  const card = h('div', { class: 'bk', part: `blocks blocks-${str(it.name) || 'card'}` })
  let group: HTMLElement | null = null
  for (const b of list(it.blocks) as Block[]) {
    if (b.type !== 'row') group = null
    const el = block(b, c, values, answer, card, onAction)
    if (!el) continue
    if (b.type === 'row') {
      if (!group) { group = h('div', { class: 'bk-list', part: 'block-list' }); card.append(group) }
      group.append(el)
    } else card.append(el)
  }
  return card
}

function block(b: Block, c: RendererContext, values: Record<string, unknown>, answer: Answer | null, card: HTMLElement, onAction?: OnAction): HTMLElement | null {
  const part = `block-${b.type}`
  switch (b.type) {
    case 'title':
      return h('div', { class: 'bk-title', part }, h('div', { class: 'card-q' }, str(b.text)), b.subtitle ? h('div', { class: 'muted' }, str(b.subtitle)) : null)
    case 'text': { const e = md(b.text, `bk-text${tone(b.tone)}`); e.setAttribute('part', part); return e }
    case 'note': { const e = md(b.text, 'bk-note muted'); e.setAttribute('part', part); return e }
    case 'row':
      return h('div', { class: `bk-row${tone(b.tone)}`, part }, b.icon ? icon(str(b.icon)) : null,
        h('span', { class: 'bk-label' }, str(b.label)), h('span', { class: 'bk-value' }, str(b.value)))
    case 'divider': return h('hr', { class: 'bk-hr', part })
    case 'image': {
      const src = safeUrl(b.src, true)
      if (!src) return null
      const ratio = ({ '1:1': '1 / 1', '4:3': '4 / 3', '16:9': '16 / 9' } as Record<string, string>)[str(b.ratio)] ?? '16 / 9'
      return h('img', { class: 'bk-img', part, src, alt: str(b.alt), loading: 'lazy', referrerpolicy: 'no-referrer', style: `aspect-ratio: ${ratio}` })
    }
    case 'place': {
      const src = safeUrl(b.image, true)
      const rating = Number(b.rating)
      return h('div', { class: 'bk-place', part },
        src ? h('img', { src, alt: '', loading: 'lazy', referrerpolicy: 'no-referrer' }) : h('span', { class: 'bk-avatar' }, str(b.title).slice(0, 1).toUpperCase()),
        h('div', { class: 'bk-place-t' }, h('div', { class: 'bk-strong' }, str(b.title)),
          b.subtitle ? h('div', { class: 'muted' }, str(b.subtitle)) : null),
        Number.isFinite(rating) && rating > 0 ? h('span', { class: 'bk-rating' }, `★ ${rating.toFixed(1)}`) : null)
    }
    case 'stat':
      return h('div', { class: `bk-stat${tone(b.tone)}`, part }, h('div', { class: 'bk-big' }, str(b.value)), b.label ? h('div', { class: 'muted' }, str(b.label)) : null)
    case 'diff':
      return h('div', { class: 'bk-diff', part }, b.label ? h('div', { class: 'muted bk-small' }, str(b.label)) : null,
        h('div', null, h('s', { class: 'muted' }, str(b.from)), h('span', { class: 'bk-arrow', 'aria-hidden': 'true' }, '→'), h('b', null, str(b.to))))
    case 'steps': {
      const items = list(b.items)
      const left = items.filter((x) => !x.done).length
      return h('div', { class: 'bk-steps', part }, b.title ? h('div', { class: 'bk-strong' }, str(b.title).replace('{left}', String(left))) : null,
        h('ul', null, items.map((x) => h('li', { class: x.done ? 'done' : '' }, h('span', { class: 'bk-check' }, x.done ? icon('check') : null), str(x.label)))))
    }
    case 'progress': {
      const max = Number(b.max) || 100
      const pct = Math.max(0, Math.min(100, (Number(b.value) / max) * 100 || 0))
      return h('div', { class: 'bk-progress', part }, b.label ? h('div', { class: 'muted bk-small' }, str(b.label)) : null,
        h('div', { class: 'bk-bar', role: 'progressbar', 'aria-valuenow': String(Math.round(pct)), 'aria-valuemin': '0', 'aria-valuemax': '100' }, h('i', { style: `width: ${pct}%` })))
    }
    case 'choice': case 'swatches': {
      const name = str(b.name) || b.type
      const multiple = !!b.multiple
      const picked = new Set<string>()
      const wrap = h('div', { class: b.type === 'swatches' ? 'bk-swatches' : 'chips', part, role: multiple ? 'group' : 'radiogroup' })
      for (const o of options(b.type === 'swatches' ? b.items : b.options)) {
        const id = str(o.id)
        const sw = b.type === 'swatches'
          ? h('button', { class: 'bk-sw', type: 'button', 'aria-label': str(o.label) || id, 'aria-pressed': 'false' },
            h('span', { class: 'bk-sw-c' }, (Array.isArray(o.colors) ? o.colors : []).slice(0, 4).map((col) => h('i', { style: `background: ${/^#[0-9a-f]{3,8}$/i.test(str(col)) ? col : 'transparent'}` }))),
            o.label ? h('span', { class: 'bk-small' }, str(o.label)) : null)
          : h('button', { class: 'chip', part: 'chip', type: 'button', 'aria-pressed': 'false' }, str(o.label))
        sw.addEventListener('click', () => {
          if (!multiple) { picked.clear(); wrap.querySelectorAll('[aria-pressed]').forEach((x) => { x.setAttribute('aria-pressed', 'false'); x.classList.remove('on') }) }
          if (picked.has(id)) picked.delete(id); else picked.add(id)
          sw.setAttribute('aria-pressed', String(picked.has(id))); sw.classList.toggle('on', picked.has(id))
          values[name] = multiple ? [...picked] : [...picked][0] ?? null
          card.dispatchEvent(new Event('bk-change'))
        })
        wrap.append(sw)
      }
      return wrap
    }
    case 'field': {
      const name = str(b.name)
      const type = ['text', 'tel', 'email', 'number', 'date', 'url'].includes(str(b.input)) ? str(b.input) : 'text'
      const input = h('input', { class: 'text-in', part: 'text-input', type, name, placeholder: str(b.placeholder), value: str(b.value),
        'aria-label': str(b.label) || name, inputmode: type === 'tel' ? 'tel' : null,
        oninput: (e: Event) => { values[name] = (e.target as HTMLInputElement).value; card.dispatchEvent(new Event('bk-change')) } }) as HTMLInputElement
      if (b.value != null) values[name] = str(b.value)
      return h('label', { class: 'bk-field', part }, b.label ? h('span', { class: 'muted bk-small' }, str(b.label)) : null, input)
    }
    case 'buttons': {
      const row = h('div', { class: 'acts', part })
      for (const x of list(b.items)) {
        const style = ({ primary: 'pri', secondary: 'sec', plain: 'link', danger: 'danger' } as Record<string, string>)[str(x.style)] ?? 'sec'
        const label = str(x.label)
        const btn = h('button', { class: `btn ${style}`, part: style === 'pri' ? 'button button-primary' : 'button button-secondary', type: 'button' }, label) as HTMLButtonElement
        btn.addEventListener('click', async () => {
          if (onAction && await onAction(str(x.id) || label, label, { ...values })) return   // the host handled it
          if (!answer) return void c.chat.send(label)   // a display card: nobody waits, the button speaks for the user
          const need = [...card.querySelectorAll<HTMLInputElement>('input[required]')].find((i) => !i.value.trim())
          if (need && x.needs !== false && style === 'pri') { need.focus(); return }
          answer(str(x.id) || label, label, { ...values }, x)
        })
        row.append(btn)
      }
      return row
    }
    case 'links': {   // a link without a value (no phone given) is left out; no links, no block
      const items = list(b.items).filter((x) => x.value != null && x.value !== '')
      return items.length ? h('div', { class: 'bk-links', part }, items.map((x) => linkEl(x, c))) : null
    }
    default:
      return null
  }
}

/** How a blocks card fills the form: the formguide plugin's apply, its state and its Undo line. */
export interface BlocksFill {
  apply: (changes: Record<string, unknown>) => Promise<unknown>
  state: () => Promise<{ config?: { state?: Record<string, unknown> } | null; ui?: unknown }>
  undo: (line: HTMLElement, fields: { name: string; label: string; previous: unknown }[]) => void
}

/** The `blocks` renderer: a waiting card answers and folds into its result line. A button with `fills` fills those
 *  form fields first (one tap, no second card), with Undo, and the answer carries the new config. */
export function blocksRenderer(it: Interrupt, c: RendererContext, fill?: BlocksFill, onAction?: OnAction): HTMLElement {
  const shell = h('div', null)
  const err = h('div', { class: 'muted err-line', role: 'alert' })
  const fold = (label: string): HTMLElement => {
    const line = h('div', { class: 'ok-line', part: 'result' }, h('i', null, '\u2713'), h('span', null, label))
    shell.replaceChildren(...[...body.querySelectorAll('.bk-title, .bk-place')].slice(0, 1).map((x) => x.cloneNode(true)), line)
    return line
  }
  const body = blocksCard(it, c, (action, label, values, button) => {
    const fills = button.fills && typeof button.fills === 'object' ? button.fills as Record<string, unknown> : null
    if (!fills || !fill) { fold(label); c.resolve({ action, label, values }); return }
    body.querySelectorAll<HTMLButtonElement>('button').forEach((b) => { b.disabled = true })
    err.textContent = ''
    void (async () => {
      try {
        const before = (await fill.state()).config?.state ?? {}
        const config = await fill.apply(fills)
        const state = await fill.state()
        const meta = (it.fill_meta ?? {}) as Record<string, { label?: string; previous?: unknown }>
        const line = fold(label)
        fill.undo(line, Object.keys(fills).map((n) => ({ name: n, label: meta[n]?.label ?? n,
          previous: meta[n] && 'previous' in meta[n] ? meta[n].previous : before[n] ?? null })))
        c.resolve({ action, label, values, config, ui: state.ui })
      } catch (e) {
        body.querySelectorAll<HTMLButtonElement>('button').forEach((b) => { b.disabled = false })
        err.textContent = c.t('applyFailed')
        err.title = e instanceof Error ? e.message : String(e)
      }
    })()
  }, onAction)
  shell.append(body, err)
  return shell
}

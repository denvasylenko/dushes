/** formguide's cards: field changes, questions, upload requests and confirmations. */
import { easeHeight, h, mdInline, numberBox, selectBox } from '../dom'
import { shrinkImage } from '../image'
import type { ChatApi, Interrupt, RendererContext } from '../types'
import type { Ctx, Directive, FieldCardFlags } from './index'
import { feedbackEl, fieldsView, formatValue, optionsView, typedView, type Opt } from './pickers'
import { dateField } from './calendar'

interface Change {
  name: string; label: string; value: unknown; display: string; reason?: string
  previous?: unknown; previous_display?: string | null; reveal?: Directive['reveal']
  /** a dependent dropdown: applied after the other rows, its option found by `lookup` */
  deferred?: boolean; lookup?: string; after?: string[]; shape?: 'option' | 'id' | 'name'
  /** the field's role: values are formatted by it */
  kind?: string
  /** a consent the user ticks: never pre-ticked */
  consent?: boolean; doc?: { title?: string; text?: string; url?: string }; required?: boolean
  /** a soft rule from the server: shown in the row, with Why */
  issue?: { severity?: string; message: string; why?: string }
  /** low: a value read from a document that the user should check */
  confidence?: string
}

/** Large plain numbers in the chat's language (1500000 -> 1,500,000); years and short numbers stay as they are. */
export function readable(s: string | null | undefined, lang: string): string {
  const v = String(s ?? '')
  if (!/^-?\d{5,}(\.\d+)?$/.test(v)) return v
  try { return new Intl.NumberFormat(lang || undefined).format(Number(v)) } catch { return v }
}

/** The option for a deferred row in the refreshed form, in the form's own shape; null when it is not there. */
function lookupOption(ch: Change, props: Record<string, any> | undefined): unknown { // eslint-disable-line @typescript-eslint/no-explicit-any
  const want = String(ch.lookup ?? ch.display ?? '').trim().toLowerCase()
  const o = (fieldOptions(props) ?? []).find((x) => String(x.id).toLowerCase() === want || x.label.toLowerCase() === want)
  if (!o) return null
  return ch.shape === 'id' ? o.id : ch.shape === 'name' ? o.label : o.raw
}

const KEY_PAIRS: [string, string][] = [['id', 'name'], ['value', 'label'], ['key', 'label'], ['value', 'text'], ['code', 'name'], ['code', 'title'], ['id', 'label']]

/** A field's options from the form's props, as {id, label, raw} (the same key detection as the backend). */
function fieldOptions(props: Record<string, any> | undefined): { id: unknown; label: string; raw: unknown }[] | null { // eslint-disable-line @typescript-eslint/no-explicit-any
  const o = props?.options ?? props?.items ?? props?.choices
  if (!o) return null
  if (!Array.isArray(o)) return Object.entries(o).map(([k, v]) => ({ id: k, label: String(v), raw: k }))
  return o.map((x) => {
    if (x && typeof x === 'object') {
      const pair = KEY_PAIRS.find(([a, b]) => a in x && b in x)
      return pair ? { id: x[pair[0]], label: String(x[pair[1]]), raw: x } : { id: JSON.stringify(x), label: JSON.stringify(x), raw: x }
    }
    return { id: x, label: String(x), raw: x }
  })
}

/** An editor for one change; returns the element and a getter of [value, display]. */
function editor(ch: Change, props: Record<string, any> | undefined, c: RendererContext): { el: HTMLElement; read: () => [unknown, string] } { // eslint-disable-line @typescript-eslint/no-explicit-any
  const v = ch.value
  const opts = fieldOptions(props)
  if (opts && opts.length) {
    const sel = h('select', { 'aria-label': ch.label })
    const current = opts.findIndex((o) => o.raw === v || String(o.id) === String((v as any)?.id ?? (v as any)?.value ?? v) || o.label === v) // eslint-disable-line @typescript-eslint/no-explicit-any
    opts.forEach((o, i) => sel.appendChild(h('option', { value: String(i), selected: i === current }, o.label)))
    return {
      el: selectBox(sel),
      read: () => {
        const o = opts[Number(sel.value)]
        // the same shape as the proposed value: the option object, its id, or its label
        const val = v && typeof v === 'object' ? o.raw : typeof v === 'string' && v === ch.display && v !== String(o.id) ? o.label : o.id
        return [val, o.label]
      },
    }
  }
  if (typeof v === 'boolean') {
    const cb = h('input', { type: 'checkbox', checked: v, 'aria-label': ch.label }) as HTMLInputElement
    return { el: cb, read: () => [cb.checked, cb.checked ? '✓' : '✗'] }
  }
  const type = typeof v === 'number' ? 'number' : typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) ? 'date' : 'text'
  const inp = h('input', { type, value: String(v ?? ''), 'aria-label': ch.label }) as HTMLInputElement
  if (type === 'date') {   // our own calendar, not the browser's
    const f = dateField({ lang: c.chat.lang, value: String(v ?? ''), label: ch.label, t: c.t, onChange: (d) => { inp.value = d } })
    return { el: f.el, read: () => [inp.value || f.value(), inp.value || f.value()] }
  }
  return {
    el: type === 'number' ? numberBox(inp) : inp,
    read: () => {
      const raw = inp.value
      const val = type === 'number' ? (raw === '' ? null : Number(raw)) : raw
      return [val, raw]
    },
  }
}

/** "Fill in 3 fields", with the language's plural form. */
function fillLabel(c: RendererContext, n: number): string {
  const form = new Intl.PluralRules(c.chat.lang).select(n)
  const word = c.t(`field_${form}`) !== `field_${form}` ? c.t(`field_${form}`) : c.t('field_other')
  return c.t('fillFields', { n, fields: word })
}

/** True on a mouse or trackpad: there, focusing a new card is helpful; on a touch screen it is not. */
export const finePointer = (): boolean => typeof matchMedia !== 'function' || matchMedia('(pointer: fine)').matches

/** An Undo link on a result line: puts the previous values back and tells the agent. Gone after a while. */
function undoButton(line: HTMLElement, c: RendererContext, ctx: Ctx, fields: { name: string; label: string; previous: unknown }[]): void {
  if (!ctx.flags.undo) return
  const undo = h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: async () => {
    undo.setAttribute('disabled', '')
    try {
      await (ctx.revertChanges ?? ctx.applyChanges)(Object.fromEntries(fields.map((f) => [f.name, f.previous])))
      line.querySelector('span')!.textContent = c.t('undone')
      await whenIdle(c.chat)
      void c.chat.send(c.t('undoneMsg', { fields: fields.map((f) => f.label).join(', ') }))
    } catch { undo.removeAttribute('disabled') }
  } }, c.t('undo'))
  line.appendChild(undo)
  setTimeout(() => undo.remove(), (ctx.undoSeconds ?? 20) * 1000)
}

/** "✓ Filled in · Make, Year" with Undo: the line an applied card or action chip leaves. */
export function appliedLine(c: RendererContext, ctx: Ctx, fields: { name: string; label: string; previous: unknown }[]): HTMLElement {
  const line = h('div', { class: 'ok-line' }, h('i', null, '\u2713'),
    h('span', null, `${c.t('filled')} \u00b7 ${fields.map((f) => f.label).join(', ')}`))
  undoButton(line, c, ctx, fields)
  return line
}

/** Undo on any result line (used by the review card's fixes). */
export const undoLine = undoButton

const whenIdle = (chat: ChatApi): Promise<void> => new Promise((ok) => {
  if (!chat.busy) return ok()
  const f = () => { chat.host.removeEventListener('agui:run-end', f); chat.host.removeEventListener('agui:error', f); ok() }
  chat.host.addEventListener('agui:run-end', f)
  chat.host.addEventListener('agui:error', f)
})

// ---------------------------------------------------------------- field changes

export function fieldCard(it: Interrupt, c: RendererContext, ctx: Ctx): HTMLElement {
  const flags: FieldCardFlags = { ...ctx.flags, ...(c.flags as Partial<FieldCardFlags>) }
  const changes: Change[] = it.changes ?? []
  const keep = new Set(changes.filter((x) => !x.consent).map((x) => x.name))   // consents start unticked
  const edits = new Map<string, [unknown, string]>()
  const many = changes.length > 1
  const err = h('div', { class: 'muted', role: 'alert' })
  const primary = h('button', { class: 'btn pri', type: 'button' }, fillLabel(c, changes.length)) as HTMLButtonElement
  const consents = changes.filter((x) => x.consent)
  const sync = () => {
    const missing = consents.filter((x) => x.required !== false && !keep.has(x.name)).length
    primary.disabled = keep.size === 0 || missing > 0
    primary.textContent = missing ? c.t('tickMore', { n: missing })
      : consents.length === changes.length ? c.t('agree')
        : keep.size === changes.length ? fillLabel(c, keep.size) : c.t('fillN', { n: keep.size, total: changes.length })
  }
  // one reason for every row: said once under the title
  const reasons = new Set(changes.map((x) => (x.reason ?? '').trim()))
  const shared = changes.length > 1 && reasons.size === 1 ? [...reasons][0] : ''
  const source = it.source as { kind?: string; title?: string; attachment_id?: string; found?: number } | undefined
  let props: Record<string, any> = {} // eslint-disable-line @typescript-eslint/no-explicit-any
  void Promise.resolve(ctx.getState()).then((s) => { props = s.config?.props ?? {} }).catch(() => {})

  const rows = changes.map((ch) => {
    const lang = c.chat.lang
    const yesNo = { yes: c.t('yes'), no: c.t('no') }
    const valueEl = h('b', null, ch.consent ? '' : formatValue(ch.display, ch.kind, lang, yesNo))
    const row = h('label', { class: `row${ch.consent ? ' consent' : ''}` })   // the whole row toggles its checkbox
    const check = (flags.select && many) || ch.consent
      ? h('input', { type: 'checkbox', checked: !ch.consent, 'aria-label': ch.label, onchange: (e: Event) => {
          if ((e.target as HTMLInputElement).checked) keep.add(ch.name); else keep.delete(ch.name)
          row.classList.toggle('off', !keep.has(ch.name))
          sync()
        } })
      : null
    const prev = flags.diff && ch.previous_display && ch.previous_display !== ch.display
      ? h('s', { class: 'muted was' }, formatValue(ch.previous_display, ch.kind, lang, yesNo)) : null
    const afterLabels = (ch.after ?? []).map((n) => changes.find((x) => x.name === n)?.label ?? n).join(', ')
    const docText = ch.doc?.text ? h('div', { class: 'muted doc', hidden: true }, ch.doc.text) : null
    const why = ch.issue?.why ? h('div', { class: 'muted why', hidden: true }, ch.issue.why) : null
    const line = h('div', { class: 'row-main' },
      ch.consent ? h('div', null, ch.label, ch.required === false ? h('span', { class: 'muted' }, ` \u00b7 ${c.t('optional')}`) : null)
        : h('div', { class: 'muted row-label' }, ch.label),
      ch.consent ? null : h('div', null, prev, valueEl,
        ch.confidence === 'low' ? h('span', { class: 'tag warn' }, c.t('check')) : null,
        ch.deferred && afterLabels ? h('span', { class: 'muted after' }, ` \u00b7 ${c.t('after', { field: afterLabels })}`) : null),
      ch.issue ? h('div', { class: `issue-line ${ch.issue.severity === 'error' ? 'error' : 'warning'}` }, ch.issue.message,
        why ? h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: (e: Event) => { e.preventDefault(); why.hidden = !why.hidden } }, c.t('why')) : null) : null,
      why, docText,
      flags.reason && !shared && ch.reason && ch.reason.trim().toLowerCase() !== String(ch.display).trim().toLowerCase()
        ? h('div', { class: 'muted' }, ch.reason) : null)
    const tools = h('div', { class: 'row-tools' })
    if (ch.doc && (ch.doc.text || ch.doc.url)) {
      tools.appendChild(ch.doc.text
        ? h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: (e: Event) => {
            e.preventDefault()
            docText!.hidden = !docText!.hidden
            ;(e.target as HTMLElement).textContent = docText!.hidden ? c.t('read') : c.t('hide')
          } }, c.t('read'))
        : h('a', { class: 'btn link', href: ch.doc.url, target: '_blank', rel: 'noopener noreferrer', 'data-keep': true }, c.t('read')))
    }
    if (flags.edit && !ch.deferred && !ch.consent) {
      tools.appendChild(h('button', { class: 'btn link', type: 'button', onclick: () => {
        const ed = editor(ch, props[ch.name], c)
        const done = h('button', { class: 'btn sec', type: 'button', onclick: () => {
          const [val, shown] = ed.read()
          if (JSON.stringify(val) !== JSON.stringify(ch.value)) edits.set(ch.name, [val, shown]); else edits.delete(ch.name)
          valueEl.textContent = formatValue(shown, ch.kind, lang, yesNo)
          box.replaceWith(line)
          tools.hidden = false
        } }, 'OK')
        const box = h('div', { class: 'field' }, ed.el, done)
        line.replaceWith(box)
        tools.hidden = true
        ;(ed.el.querySelector<HTMLElement>('input, select') ?? ed.el).focus()
      } }, c.t('edit')))
    }
    if (flags.jump && ch.reveal && !ch.consent) {
      tools.appendChild(h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: () =>
        (ctx.onDirective ?? (() => {}))({ type: 'focus', target: ch.name, reveal: ch.reveal ?? [], hint: '' }) }, c.t('jump')))
    }
    row.append(...[check, line, tools].filter(Boolean) as HTMLElement[])
    row.dataset.name = ch.name
    return row
  })

  const acts = h('div', { class: 'acts' }, primary,
    h('button', { class: 'btn sec', type: 'button', onclick: () => { status(false, []); c.resolve({ accepted: false }) } }, c.t('reject')))
  const head = source?.kind === 'document'
    ? h('div', { class: 'doc-head' },
        source.attachment_id ? h('img', { class: 'thumb', alt: '', src: `${ctx.base(c.chat)}/attachments/${encodeURIComponent(source.attachment_id)}?thread_id=${encodeURIComponent(c.chat.threadId)}`,
          onerror: (e: Event) => { (e.target as HTMLElement).replaceWith(h('span', { class: 'thumb', 'aria-hidden': 'true' })) } }) : h('span', { class: 'thumb', 'aria-hidden': 'true' }),
        h('div', null, h('b', null, source.title ?? ''),
          h('div', { class: 'muted' }, [c.t('foundN', { n: source.found ?? changes.length }),
            ...(changes.some((x) => x.confidence === 'low') ? [c.t('toCheck', { n: changes.filter((x) => x.confidence === 'low').length })] : [])].join(' \u00b7 '))))
    : h('div', { class: 'card-t' }, consents.length === changes.length ? c.t('consentTitle') : c.t('fillTitle'))
  const card = h('div', { class: 'fcard' }, head, shared && flags.reason ? h('div', { class: 'muted shared' }, shared) : null, ...rows, err, acts)

  const status = (ok: boolean, applied: Change[], partial = false) => {
    const names = applied.map((x) => x.label).join(', ')
    const word = ok ? (partial ? c.t('partly') : c.t('filled')) : c.t('rejected')
    const toggle = h('button', { class: 'fold', type: 'button', 'data-keep': true, 'aria-expanded': 'false', title: names || null, onclick: () => {
      const open = card.classList.toggle('unfolded')
      toggle.setAttribute('aria-expanded', String(open))
    } }, h('i', null, ok ? '\u2713' : '\u2715'), h('span', null, ok && names ? `${word} \u00b7 ${names}` : word),
      h('span', { class: 'chev', 'aria-hidden': 'true' }, '\u203a'))   // the line opens to show the rows again
    const line = h('div', { class: `ok-line${ok ? '' : ' off'}` }, toggle)
    if (ok) undoButton(line, c, ctx, applied.map((x) => ({ name: x.name, label: x.label, previous: x.previous ?? null })))
    acts.replaceWith(line)
    card.querySelectorAll('.row .btn.link:not([data-keep])').forEach((b) => b.remove())   // no editing after the answer
    card.classList.add('folded')   // the rows fold into the line; a click on it shows them again
  }

  primary.addEventListener('click', async () => {
    const kept = changes.filter((x) => keep.has(x.name))
    if (!kept.length) return
    primary.disabled = true
    err.textContent = ''
    const now = kept.filter((x) => !x.deferred)
    const values = Object.fromEntries(now.map((x) => [x.name, edits.has(x.name) ? edits.get(x.name)![0] : x.value]))
    try {
      let config = now.length ? await ctx.applyChanges(values) : (await ctx.getState()).config
      let state = await ctx.getState()
      for (const ch of kept.filter((x) => x.deferred)) {   // dependent dropdowns: their options exist now
        const v = lookupOption(ch, state.config?.props?.[ch.name])
        const row = rows.find((r) => r.dataset.name === ch.name)
        if (v === null || v === undefined) {
          keep.delete(ch.name)
          row?.classList.add('off')
          row?.querySelector('.row-main')?.appendChild(h('div', { class: 'muted' }, c.t('notAvailable')))
          continue
        }
        config = await ctx.applyChanges({ [ch.name]: v })
        state = await ctx.getState()
      }
      const applied = kept.filter((x) => keep.has(x.name))
      if (!applied.length) throw new Error(c.t('notAvailable'))
      const partial = applied.length < changes.length
      const edited = Object.fromEntries([...edits].filter(([k]) => keep.has(k)).map(([k, v]) => [k, v[0]]))
      status(true, applied, partial)
      c.resolve({ accepted: true, config, ui: state.ui, ...(partial ? { names: applied.map((x) => x.name) } : {}),
        ...(Object.keys(edited).length ? { edited } : {}) })
      const last = applied[applied.length - 1]
      if (last.reveal && ctx.onDirective) ctx.onDirective({ type: 'focus', target: last.name, reveal: last.reveal, hint: '' })
    } catch (e) {
      err.textContent = c.t('applyFailed')
      err.title = e instanceof Error ? e.message : String(e)
      primary.disabled = false
    }
  })
  sync()
  return card
}

// ---------------------------------------------------------------- questions

const INPUT: Record<string, string> = { date: 'date', time: 'time', datetime: 'datetime-local', number: 'number', text: 'text' }

/** A question line with inline markdown (**bold** from the model). */
const qText = (s: unknown): HTMLElement => { const el = h('div', { class: 'card-q' }); el.innerHTML = mdInline(String(s ?? '')); return el }

/** Typed text that reads like a field's value, not a question or a story. */
const valueLike = (t: string): boolean => t.length <= 120 && !t.includes('\n') && !/[?\u061f\uff1f]\s*$/.test(t)   // ? in Latin, Arabic, CJK

export function askCard(it: Interrupt, c: RendererContext, ctx?: Ctx): HTMLElement {
  const options: Opt[] = it.options ?? []
  const multiple = !!it.multiple
  const applies = !!(it.applies && it.field && ctx)   // tapping an option fills the field (no second card)
  const picked = new Set<string>()
  const err = h('div', { class: 'muted err-line', role: 'alert' })
  const answered = (labels: string, ok = true) => {   // the card shrinks to the question and the answer, easing (no jump)
    const line = h('div', { class: `ok-line${ok ? '' : ' off'}` }, h('i', null, ok ? '\u2713' : '\u2715'), h('span', null, labels))
    easeHeight(card, () => {
      acts.replaceWith(line)
      card.querySelectorAll('.chips, .opts, .cmp, .strip, .range, .fields, .search, .note, .num').forEach((x) => x.remove())
      text?.remove()
      err.remove()
    })
    return line
  }
  /** Values that fill fields directly (a day, a slot, a range, several fields): applied with Undo, then resumed. */
  const applyValues = async (values: Record<string, unknown>, labels: string, answer: Record<string, unknown>, strict = false) => {
    card.querySelectorAll<HTMLButtonElement>('.chip, .btn, .opt').forEach((b) => { b.disabled = true })
    err.textContent = ''
    try {
      const prev = (await ctx!.getState()).config?.state ?? {}
      const config = await ctx!.applyChanges(values)
      // a typed text the form rejects ("4 digits"): put the old value back and let the assistant handle the answer
      const rejected = strict && Object.keys(values).some((n) => (config as { props?: Record<string, { error?: unknown }> })?.props?.[n]?.error)
      if (rejected) {
        await ctx!.applyChanges(Object.fromEntries(Object.keys(values).map((n) => [n, n === it.field ? it.previous ?? prev[n] ?? null : prev[n] ?? null])))
        answered(labels)
        c.resolve(answer)
        return
      }
      const state = await ctx!.getState()
      const line = answered(labels)
      const names = Object.keys(values)
      const label = (n: string) => (it.fields ?? []).find((f: { name: string }) => f.name === n)?.label ?? (n === it.field ? it.label : null) ?? n
      undoButton(line, c, ctx!, names.map((n) => ({ name: n, label: label(n), previous: n === it.field ? it.previous ?? prev[n] ?? null : prev[n] ?? null })))
      c.resolve({ ...answer, config, ui: state.ui })
      ctx!.onDirective?.({ type: 'focus', target: names[names.length - 1], reveal: it.reveal ?? [], hint: '' })
    } catch (e) {
      card.querySelectorAll<HTMLButtonElement>('.chip, .btn, .opt').forEach((b) => { b.disabled = false })
      err.textContent = c.t('applyFailed')
      err.title = e instanceof Error ? e.message : String(e)
    }
  }
  /** A typed answer from a richer control: fills the field when the card applies, else just answers. */
  const commitTyped = (value: unknown, label: string) => {
    if (applies) return void applyValues({ [it.field]: value }, label, { answer: { text: String(value) } })
    answered(label)
    c.resolve({ answer: { text: String(value) } })
  }
  const fill = async (ids: string[], labels: string) => {
    const chosen = ids.map((i) => options.find((o) => o.id === i)!)
    const value = multiple ? chosen.map((o) => o.value) : chosen[0].value
    card.querySelectorAll<HTMLButtonElement>('.chip, .btn').forEach((b) => { b.disabled = true })
    err.textContent = ''
    try {
      const config = await ctx!.applyChanges({ [it.field]: value })
      const state = await ctx!.getState()
      const line = answered(labels)
      undoButton(line, c, ctx!, [{ name: it.field, label: it.label ?? it.field, previous: it.previous ?? null }])
      c.resolve({ answer: { ids }, config, ui: state.ui })
      ctx!.onDirective?.({ type: 'focus', target: it.field, reveal: it.reveal ?? [], hint: '' })   // show the field it filled
    } catch (e) {
      card.querySelectorAll<HTMLButtonElement>('.chip, .btn').forEach((b) => { b.disabled = false })
      err.textContent = c.t('applyFailed')
      err.title = e instanceof Error ? e.message : String(e)
    }
  }
  const send = (ids: string[], text: string) => {
    const labels = [...ids.map((i) => options.find((o) => o.id === i)?.label ?? i), ...(text ? [`"${text}"`] : [])].join(', ')
    if (applies && ids.length && !text) return void fill(ids, labels)
    // a question about a text field: the typed value fills it at once (one tap); a question back ("why?") or a
    // long story goes to the assistant instead
    if (applies && !ids.length && text && !options.length && !it.input?.type?.match(/^(date|time|number)$/) && valueLike(text)) {
      return void applyValues({ [it.field]: text }, labels, { answer: { text } }, true)
    }
    answered(labels)
    c.resolve({ answer: { ...(ids.length ? { ids } : {}), ...(text ? { text } : {}) } })
  }
  const pick = (o: Opt, b: HTMLButtonElement) => {
    if (!multiple) return send([o.id], '')
    if (picked.has(o.id)) picked.delete(o.id); else picked.add(o.id)
    b.classList.toggle('on', picked.has(o.id))
    b.setAttribute('aria-pressed', String(picked.has(o.id)))
    sync()
  }
  // keyboard hints 1-9 would read as part of the answer when the options are numbers ("2 1", "3 2")
  const numeric = options.some((o) => /\d/.test(o.label))
  const chipFor = (o: Opt, i: number) => {
    const b = h('button', { class: 'chip', part: 'chip', type: 'button', 'aria-pressed': multiple ? 'false' : null },
      i < 9 && !numeric ? h('kbd', null, String(i + 1)) : null, o.label) as HTMLButtonElement
    b.addEventListener('click', () => pick(o, b))
    return b
  }
  const view = optionsView(it, c, options, pick, chipFor)
  const chips = view.buttons
  const inp = it.input as { type?: string; min?: string | number; max?: string | number } | undefined
  const text = it.allow_text === false ? null : h('input', {
    class: 'text-in', type: INPUT[inp?.type ?? 'text'] ?? 'text', min: inp?.min, max: inp?.max,
    placeholder: options.length ? c.t('orType') : c.t('typeAnswer'), 'aria-label': c.t('typeAnswer'),
    onkeydown: (e: KeyboardEvent) => { if (e.key === 'Enter') { e.preventDefault(); submit() } },
    oninput: () => sync(),
  }) as HTMLInputElement | null
  const submit = () => {
    const t = text?.value.trim() ?? ''
    const ids = multiple ? [...picked] : []
    if (ids.length || t) send(ids, t)
  }
  const typed = !it.fields?.length ? typedView(it, c, ctx, commitTyped, text) : null
  const several = it.fields?.length && ctx
    ? fieldsView(it, c, ctx, (values, labels) => applyValues(values, labels, { answers: values })) : null
  if (several) text?.remove()
  const sendBtn = h('button', { class: 'btn pri', type: 'button', onclick: submit }, c.t('send')) as HTMLButtonElement
  // single choice: the chips are the answer, Send appears only for typed text
  const sync = () => { sendBtn.disabled = !(picked.size || text?.value.trim()); sendBtn.hidden = !multiple && !text?.value.trim() }
  const acts = h('div', { class: 'acts' }, (multiple || (text && !several)) ? sendBtn : null,
    h('button', { class: 'btn link', type: 'button', onclick: () => { answered(c.t('skipped'), false); c.resolve({ accepted: false }) } }, c.t('skip')))
  const card = h('div', { tabindex: 0, 'aria-label': String(it.question ?? '').replace(/[*`]/g, '') },
    qText(it.question),
    view.el, typed, several || !text ? null : text.type === 'number' ? numberBox(text) : text, several, err, acts)
  card.addEventListener('keydown', (e) => {   // 1..9 picks an option
    if (e.target instanceof HTMLInputElement) return
    const n = Number(e.key)
    if (n >= 1 && n <= chips.length) { e.preventDefault(); chips[n - 1].click() }
  })
  sync()
  if (!options.length && text && !text.hidden && !typed && !several && finePointer()) text.setAttribute('autofocus', '')
  return card
}

// ---------------------------------------------------------------- upload requests

function uploadOne(url: string, threadId: string, file: File, onProgress: (f: number) => void): Promise<{ id: string; filename: string }> {
  return new Promise((ok, fail) => {
    const x = new XMLHttpRequest()
    x.open('POST', url)
    x.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total) }
    x.onload = () => {
      if (x.status >= 200 && x.status < 300) ok(JSON.parse(x.responseText))
      else { let d = x.statusText; try { d = JSON.parse(x.responseText).detail ?? d } catch { /* text */ } fail(new Error(d)) }
    }
    x.onerror = () => fail(new Error('network error'))
    const body = new FormData()
    body.append('thread_id', threadId)
    body.append('file', file)
    x.send(body)
  })
}

export function uploadCard(it: Interrupt, c: RendererContext, ctx: Ctx): HTMLElement {
  const picker = h('input', { type: 'file', accept: it.accept, multiple: !!it.multiple, hidden: true }) as HTMLInputElement
  const bar = h('div', { class: 'bar', hidden: true }, h('div'))
  const msg = h('div', { class: 'muted', role: 'status' })
  const zone = h('div', {
    class: 'zone',
    tabindex: 0, role: 'button',
    onclick: () => picker.click(),
    onkeydown: (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); picker.click() } },
    ondragover: (e: DragEvent) => { e.preventDefault(); zone.classList.add('over') },
    ondragleave: () => { zone.classList.remove('over') },
    ondrop: (e: DragEvent) => { e.preventDefault(); zone.classList.remove('over'); void go([...(e.dataTransfer?.files ?? [])]) },
  }, h('div', null, `${c.t('drop')} `, h('span', { class: 'link-text' }, c.t('pick'))),
    h('div', { class: 'muted' }, String(it.accept ?? '').replaceAll(',', ', ')))
  picker.addEventListener('change', () => void go([...(picker.files ?? [])]))
  let busy = false
  const go = async (files: File[]) => {
    if (busy || !files.length) return
    files = it.multiple ? files : files.slice(0, 1)
    busy = true
    bar.hidden = false
    msg.textContent = c.t('uploading')
    files = await Promise.all(files.map((f) => shrinkImage(f, c.chat.options.imageMaxPx)))   // big photos -> JPEG
    const fill = bar.firstElementChild as HTMLElement
    const ids: string[] = []
    try {
      for (let i = 0; i < files.length; i++) {
        const r = await uploadOne(`${ctx.base(c.chat)}/attachments`, c.chat.threadId, files[i],
          (f) => { fill.style.width = `${Math.round(((i + f) / files.length) * 100)}%` })
        ids.push(r.id)
      }
      fill.style.width = '100%'
      acts.replaceWith(h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, `${c.t('uploaded')}: ${files.map((f) => f.name).join(', ')}`)))
      // the card folds like the others: the request and its result line, nothing else (no full progress bar)
      zone.remove(); phoneActs?.remove(); bar.remove(); msg.remove(); privacy?.remove()
      c.resolve({ attachment_ids: ids })
    } catch (e) {
      msg.textContent = `${c.t('uploadFailed')}: ${e instanceof Error ? e.message : e}`
      bar.hidden = true
      busy = false
    }
  }
  // phones: the camera first (when images are accepted), the file picker second
  const images = !it.accept || /image|\.(png|jpe?g|webp|heic|gif)/i.test(String(it.accept))
  const touch = !finePointer()
  const camera = images && touch ? h('input', { type: 'file', accept: 'image/*', capture: 'environment', hidden: true,
    onchange: (e: Event) => void go([...((e.target as HTMLInputElement).files ?? [])]) }) as HTMLInputElement : null
  const phoneActs = camera ? h('div', { class: 'acts' },
    h('button', { class: 'btn pri', type: 'button', onclick: () => camera.click() }, c.t('takePhoto')),
    h('button', { class: 'btn sec', type: 'button', onclick: () => picker.click() }, c.t('chooseFile'))) : null
  if (phoneActs) zone.hidden = true
  const acts = h('div', { class: 'acts' },
    h('button', { class: 'btn link', type: 'button', onclick: () => {
      acts.replaceWith(h('div', { class: 'ok-line off' }, h('i', null, '✕'), h('span', null, c.t('skipped'))))
      zone.remove(); phoneActs?.remove(); msg.textContent = ''; bar.hidden = true        // a skipped request shrinks to its prompt
      c.resolve({ accepted: false })
    } }, c.t('skip')))
  const privacy = it.privacy ? h('div', { class: 'muted privacy' }, it.privacy) : null
  return h('div', null, h('div', { class: 'card-q' }, it.prompt), zone, phoneActs, picker, camera, bar, msg, privacy, acts)
}

// ---------------------------------------------------------------- confirmations

export function confirmCard(it: Interrupt, c: RendererContext, ctx?: Ctx): HTMLElement {
  const answer = (ok: boolean) => {
    const line = h('div', { class: `ok-line${ok ? '' : ' off'}` }, h('i', null, ok ? '✓' : '✕'), h('span', null, ok ? c.t('confirmed') : c.t('declined')))
    easeHeight(acts.closest<HTMLElement>('.card'), () => acts.replaceWith(line))
    c.resolve({ accepted: ok })
    // a receipt (CUSTOM receipt) may replace the line later; the rating is offered once either way
    if (ok && ctx && !c.restored) line.after(feedbackEl(c, c.chat, ctx, it.card_id))
  }
  const details: { label: string; value: string }[] = Array.isArray(it.details) ? it.details.slice(0, 6) : []
  const acts = h('div', { class: 'acts' },
    h('button', { class: `btn ${it.danger ? 'danger' : 'pri'}`, type: 'button', onclick: () => answer(true) }, it.confirm_label || c.t('confirm')),
    h('button', { class: 'btn sec', type: 'button', onclick: () => answer(false) }, c.t('cancel')))
  return h('div', { role: 'alertdialog', 'aria-label': it.title },
    h('div', { class: 'card-q' }, it.title), it.message ? h('div', { class: 'card-msg' }, it.message) : null,
    details.length ? h('dl', { class: 'details' }, details.map((d) => [h('dt', { class: 'muted' }, d.label), h('dd', null, d.value)])) : null,
    it.consequence ? h('div', { class: 'card-msg consequence' }, it.consequence) : null, acts)
}

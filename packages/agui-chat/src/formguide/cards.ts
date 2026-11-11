/** formguide's cards: field changes, questions, upload requests and confirmations. */
import { h } from '../dom'
import { shrinkImage } from '../image'
import type { ChatApi, Interrupt, RendererContext } from '../types'
import type { Ctx, Directive, FieldCardFlags } from './index'

interface Change {
  name: string; label: string; value: unknown; display: string; reason?: string
  previous?: unknown; previous_display?: string | null; reveal?: Directive['reveal']
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
function editor(ch: Change, props: Record<string, any> | undefined): { el: HTMLElement; read: () => [unknown, string] } { // eslint-disable-line @typescript-eslint/no-explicit-any
  const v = ch.value
  const opts = fieldOptions(props)
  if (opts && opts.length) {
    const sel = h('select', { 'aria-label': ch.label })
    const current = opts.findIndex((o) => o.raw === v || String(o.id) === String((v as any)?.id ?? (v as any)?.value ?? v) || o.label === v) // eslint-disable-line @typescript-eslint/no-explicit-any
    opts.forEach((o, i) => sel.appendChild(h('option', { value: String(i), selected: i === current }, o.label)))
    return {
      el: sel,
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
  return {
    el: inp,
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
  const keep = new Set(changes.map((x) => x.name))
  const edits = new Map<string, [unknown, string]>()
  const many = changes.length > 1
  const err = h('div', { class: 'muted', role: 'alert' })
  const primary = h('button', { class: 'btn pri', type: 'button' }, fillLabel(c, changes.length)) as HTMLButtonElement
  const sync = () => {
    primary.disabled = keep.size === 0
    primary.textContent = keep.size === changes.length ? fillLabel(c, keep.size) : c.t('fillN', { n: keep.size, total: changes.length })
  }
  let props: Record<string, any> = {} // eslint-disable-line @typescript-eslint/no-explicit-any
  void Promise.resolve(ctx.getState()).then((s) => { props = s.config?.props ?? {} }).catch(() => {})

  const rows = changes.map((ch) => {
    const valueEl = h('b', null, ch.display)
    const row = h('div', { class: 'row' })
    const check = flags.select && many
      ? h('input', { type: 'checkbox', checked: true, 'aria-label': ch.label, onchange: (e: Event) => {
          if ((e.target as HTMLInputElement).checked) keep.add(ch.name); else keep.delete(ch.name)
          row.classList.toggle('off', !keep.has(ch.name))
          sync()
        } })
      : null
    const prev = flags.diff && ch.previous_display && ch.previous_display !== ch.display
      ? h('s', { class: 'muted was' }, ch.previous_display) : null
    const line = h('div', { class: 'row-main' },
      h('div', { class: 'muted row-label' }, ch.label),
      h('div', null, prev, valueEl),
      flags.reason && ch.reason ? h('div', { class: 'muted' }, ch.reason) : null)
    const tools = h('div', { class: 'row-tools' })
    if (flags.edit) {
      tools.appendChild(h('button', { class: 'btn link', type: 'button', onclick: () => {
        const ed = editor(ch, props[ch.name])
        const done = h('button', { class: 'btn sec', type: 'button', onclick: () => {
          const [val, shown] = ed.read()
          if (JSON.stringify(val) !== JSON.stringify(ch.value)) edits.set(ch.name, [val, shown]); else edits.delete(ch.name)
          valueEl.textContent = shown
          box.replaceWith(line)
          tools.hidden = false
        } }, 'OK')
        const box = h('div', { class: 'field' }, ed.el, done)
        line.replaceWith(box)
        tools.hidden = true
        ed.el.focus()
      } }, c.t('edit')))
    }
    if (flags.jump && ch.reveal) {
      tools.appendChild(h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: () =>
        (ctx.onDirective ?? (() => {}))({ type: 'focus', target: ch.name, reveal: ch.reveal ?? [], hint: '' }) }, c.t('jump')))
    }
    row.append(...[check, line, tools].filter(Boolean) as HTMLElement[])
    return row
  })

  const acts = h('div', { class: 'acts' }, primary,
    h('button', { class: 'btn sec', type: 'button', onclick: () => { status(false, []); c.resolve({ accepted: false }) } }, c.t('reject')))
  const card = h('div', null, h('div', { class: 'card-t' }, c.t('fillTitle')), ...rows, err, acts)

  const status = (ok: boolean, applied: Change[], partial = false) => {
    const line = h('div', { class: `ok-line${ok ? '' : ' off'}` }, h('i', null, ok ? '✓' : '✕'),
      h('span', null, ok ? (partial ? c.t('partly') : c.t('filled')) : c.t('rejected')))
    if (ok) undoButton(line, c, ctx, applied.map((x) => ({ name: x.name, label: x.label, previous: x.previous ?? null })))
    acts.replaceWith(line)
    card.querySelectorAll('.row .btn.link:not([data-keep])').forEach((b) => b.remove())   // no editing after the answer
  }

  primary.addEventListener('click', async () => {
    const kept = changes.filter((x) => keep.has(x.name))
    if (!kept.length) return
    primary.disabled = true
    err.textContent = ''
    const values = Object.fromEntries(kept.map((x) => [x.name, edits.has(x.name) ? edits.get(x.name)![0] : x.value]))
    try {
      const config = await ctx.applyChanges(values)
      const state = await ctx.getState()
      const partial = kept.length < changes.length
      const edited = Object.fromEntries([...edits].filter(([k]) => keep.has(k)).map(([k, v]) => [k, v[0]]))
      status(true, kept, partial)
      c.resolve({ accepted: true, config, ui: state.ui, ...(partial ? { names: kept.map((x) => x.name) } : {}),
        ...(Object.keys(edited).length ? { edited } : {}) })
      const last = kept[kept.length - 1]
      if (last.reveal && ctx.onDirective) ctx.onDirective({ type: 'focus', target: last.name, reveal: last.reveal, hint: '' })
    } catch (e) {
      err.textContent = e instanceof Error ? e.message : String(e)
      primary.disabled = false
    }
  })
  sync()
  return card
}

// ---------------------------------------------------------------- questions

const INPUT: Record<string, string> = { date: 'date', time: 'time', datetime: 'datetime-local', number: 'number', text: 'text' }

export function askCard(it: Interrupt, c: RendererContext, ctx?: Ctx): HTMLElement {
  const options: { id: string; label: string; value?: unknown }[] = it.options ?? []
  const multiple = !!it.multiple
  const applies = !!(it.applies && it.field && ctx)   // tapping an option fills the field (no second card)
  const picked = new Set<string>()
  const err = h('div', { class: 'muted err-line', role: 'alert' })
  const answered = (labels: string, ok = true) => {   // the card shrinks to the question and the answer
    const line = h('div', { class: `ok-line${ok ? '' : ' off'}` }, h('i', null, ok ? '\u2713' : '\u2715'), h('span', null, labels))
    acts.replaceWith(line)
    card.querySelector('.chips')?.remove()
    text?.remove()
    err.remove()
    return line
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
    } catch (e) {
      card.querySelectorAll<HTMLButtonElement>('.chip, .btn').forEach((b) => { b.disabled = false })
      err.textContent = c.t('applyFailed')
      err.title = e instanceof Error ? e.message : String(e)
    }
  }
  const send = (ids: string[], text: string) => {
    const labels = [...ids.map((i) => options.find((o) => o.id === i)?.label ?? i), ...(text ? [`"${text}"`] : [])].join(', ')
    if (applies && ids.length && !text) return void fill(ids, labels)
    answered(labels)
    c.resolve({ answer: { ...(ids.length ? { ids } : {}), ...(text ? { text } : {}) } })
  }
  const chips = options.map((o, i) => {
    const b = h('button', { class: 'chip', part: 'chip', type: 'button', 'aria-pressed': multiple ? 'false' : null },
      i < 9 ? h('kbd', null, String(i + 1)) : null, o.label) as HTMLButtonElement
    b.addEventListener('click', () => {
      if (!multiple) return send([o.id], '')
      if (picked.has(o.id)) picked.delete(o.id); else picked.add(o.id)
      b.classList.toggle('on', picked.has(o.id))
      b.setAttribute('aria-pressed', String(picked.has(o.id)))
      sync()
    })
    return b
  })
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
  const sendBtn = h('button', { class: 'btn pri', type: 'button', onclick: submit }, c.t('send')) as HTMLButtonElement
  // single choice: the chips are the answer, Send appears only for typed text
  const sync = () => { sendBtn.disabled = !(picked.size || text?.value.trim()); sendBtn.hidden = !multiple && !text?.value.trim() }
  const acts = h('div', { class: 'acts' }, (multiple || text) ? sendBtn : null,
    h('button', { class: 'btn link', type: 'button', onclick: () => { answered(c.t('skipped'), false); c.resolve({ accepted: false }) } }, c.t('skip')))
  const card = h('div', { tabindex: 0, 'aria-label': it.question },
    h('div', { class: 'card-q' }, it.question),
    options.length ? h('div', { class: 'chips' }, chips) : null,
    text, err, acts)
  card.addEventListener('keydown', (e) => {   // 1..9 picks an option
    if (e.target instanceof HTMLInputElement) return
    const n = Number(e.key)
    if (n >= 1 && n <= chips.length) { e.preventDefault(); chips[n - 1].click() }
  })
  sync()
  if (!options.length && text && finePointer()) text.setAttribute('autofocus', '')
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
      zone.remove()
      msg.textContent = ''
      c.resolve({ attachment_ids: ids })
    } catch (e) {
      msg.textContent = `${c.t('uploadFailed')}: ${e instanceof Error ? e.message : e}`
      bar.hidden = true
      busy = false
    }
  }
  const acts = h('div', { class: 'acts' },
    h('button', { class: 'btn link', type: 'button', onclick: () => {
      acts.replaceWith(h('div', { class: 'ok-line off' }, h('i', null, '✕'), h('span', null, c.t('skipped'))))
      zone.remove(); msg.textContent = ''; bar.hidden = true        // a skipped request shrinks to its prompt
      c.resolve({ accepted: false })
    } }, c.t('skip')))
  return h('div', null, h('div', { class: 'card-q' }, it.prompt), zone, picker, bar, msg, acts)
}

// ---------------------------------------------------------------- confirmations

export function confirmCard(it: Interrupt, c: RendererContext): HTMLElement {
  const answer = (ok: boolean) => {
    acts.replaceWith(h('div', { class: `ok-line${ok ? '' : ' off'}` }, h('i', null, ok ? '✓' : '✕'), h('span', null, ok ? c.t('confirmed') : c.t('declined'))))
    c.resolve({ accepted: ok })
  }
  const acts = h('div', { class: 'acts' },
    h('button', { class: `btn ${it.danger ? 'danger' : 'pri'}`, type: 'button', onclick: () => answer(true) }, it.confirm_label || c.t('confirm')),
    h('button', { class: 'btn sec', type: 'button', onclick: () => answer(false) }, c.t('cancel')))
  return h('div', { role: 'alertdialog', 'aria-label': it.title },
    h('div', { class: 'card-q' }, it.title), h('div', { class: 'card-msg' }, it.message), acts)
}

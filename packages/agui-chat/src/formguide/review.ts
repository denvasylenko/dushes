/**
 * The review card: the form's status (sections, what is left, Continue) or the check before sending (errors with
 * Fix and Show, warnings with Why). It ships with the card blocks (agui-chat.blocks.js in the one-script build,
 * loaded when a run starts); pickers.ts hands it out.
 */
import { h } from '../dom'
import type { Interrupt, RendererContext } from '../types'
import type { Ctx } from './index'

interface Section { name: string; label?: string; left: number; total?: number; reveal?: unknown[] }
interface Issue { severity: 'error' | 'warning'; field: string; label?: string; message: string; detail?: string
  fix?: { value: unknown; display?: string }; source?: { title: string; section?: string }; reveal?: unknown[] }

/** The form's status (sections, what is left, Continue) or the check before sending (errors with Fix and
 * Show, warnings with Why). The main button names what is left until nothing blocks sending. */
export function realReviewCard(it: Interrupt, c: RendererContext, ctx: Ctx,
  undoFor: (line: HTMLElement, fields: { name: string; label: string; previous: unknown }[]) => void): HTMLElement {
  const sections: Section[] = it.sections ?? []
  const issues: Issue[] = it.issues ?? []
  const show = (target: string, reveal: unknown[] = []) =>
    ctx.onDirective?.({ type: 'focus', target, reveal: reveal as never, hint: '' })
  const card = h('div', { class: 'rev' })
  const err = h('div', { class: 'muted err-line', role: 'alert' })
  const fixed = new Set<string>()
  let config: unknown = null

  if (it.mode !== 'submit') {
    const left = sections.reduce((n, s) => n + (s.left || 0), 0)
    const next = sections.find((s) => s.left > 0)
    card.append(h('div', { class: 'card-q' }, left ? c.t('leftN', { n: left }) : c.t('allDone')),
      ...sections.map((s) => h('button', { class: `row rev-s${s.left ? '' : ' done'}`, type: 'button', 'data-keep': true, onclick: () => show(s.name, s.reveal) },
        h('i', { class: s.left ? 'dot' : 'okmark', 'aria-hidden': 'true' }, s.left ? '' : '✓'),
        h('span', { class: 'row-main' }, s.label ?? s.name),
        h('span', { class: 'muted' }, s.left ? c.t('leftShort', { n: s.left }) : c.t('done')))))
    const acts = h('div', { class: 'acts' },
      next ? h('button', { class: 'btn pri', type: 'button', onclick: () => {
        acts.replaceWith(h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, next.label ?? next.name)))
        c.resolve({ action: 'continue', section: next.name })
        show(next.name, next.reveal)
      } }, c.t('continueWith', { section: next.label ?? next.name })) : null,
      h('button', { class: 'btn link', type: 'button', onclick: () => { acts.remove(); c.resolve({ accepted: false }) } }, c.t('notYet')))
    card.append(acts)
    return card
  }

  const errors = issues.filter((i) => i.severity === 'error')
  const title = h('div', { class: 'card-q' })
  const main = h('button', { class: 'btn pri', type: 'button' }) as HTMLButtonElement
  const sync = () => {
    const open = errors.filter((e) => !fixed.has(e.field)).length
    title.textContent = open ? c.t('almostN', { n: open }) : c.t('readyToSend')
    main.textContent = open ? c.t('fixToSend', { n: open }) : c.t('sendNow')
  }
  const rows = issues.map((i) => {
    const line = h('div', { class: 'row-main' }, h('div', null, i.label ? `${i.label}: ${i.message}` : i.message),
      i.detail && i.severity === 'error' ? h('div', { class: 'muted' }, i.detail) : null)
    const tools = h('div', { class: 'row-tools' })
    const row = h('div', { class: `row issue ${i.severity}` }, h('i', { class: 'sev', 'aria-hidden': 'true' }, i.severity === 'error' ? '!' : '•'), line, tools)
    if (i.severity === 'error' && i.fix) {
      const fix = h('button', { class: 'btn link', type: 'button', onclick: async () => {
        fix.setAttribute('disabled', '')
        err.textContent = ''
        try {
          const prev = (await ctx.getState()).config?.state?.[i.field] ?? null
          config = await ctx.applyChanges({ [i.field]: i.fix!.value })
          fixed.add(i.field)
          row.classList.add('fixed')
          const ok = h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, c.t('fixedTo', { value: i.fix!.display ?? String(i.fix!.value) })))
          tools.replaceChildren()
          line.append(ok)
          undoFor(ok, [{ name: i.field, label: i.label ?? i.field, previous: prev }])
          sync()
        } catch (e) {
          fix.removeAttribute('disabled')
          err.textContent = c.t('applyFailed')
          err.title = e instanceof Error ? e.message : String(e)
        }
      } }, c.t('fix'))
      tools.append(fix)
    }
    if (i.severity === 'error') tools.append(h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: () => show(i.field, i.reveal) }, c.t('jump')))
    if (i.severity === 'warning' && (i.detail || i.source)) {
      const why = h('div', { class: 'muted why', hidden: true }, i.detail ?? '',
        i.source ? h('span', { class: 'src-chip' }, `${i.source.title}${i.source.section ? ` › ${i.source.section}` : ''}`) : null)
      line.append(why)
      tools.append(h('button', { class: 'btn link', type: 'button', 'data-keep': true, onclick: () => { why.hidden = !why.hidden } }, c.t('why')))
    }
    return row
  })
  main.addEventListener('click', () => {
    const open = errors.find((e) => !fixed.has(e.field))
    if (open) return show(open.field, open.reveal)   // the button points at what still blocks sending
    acts.replaceWith(h('div', { class: 'ok-line' }, h('i', null, '✓'), h('span', null, c.t('readyToSend'))))
    card.querySelectorAll('.row-tools .btn:not([data-keep])').forEach((b) => b.remove())
    c.resolve(fixed.size ? { action: 'fixed', names: [...fixed], config } : { action: 'submit' })
  })
  const acts = h('div', { class: 'acts' }, main,
    h('button', { class: 'btn link', type: 'button', onclick: () => {
      acts.remove()
      c.resolve(fixed.size ? { action: 'fixed', names: [...fixed], config } : { accepted: false })
    } }, c.t('notYet')))
  sync()
  card.append(title, ...rows, err, acts)
  return card
}


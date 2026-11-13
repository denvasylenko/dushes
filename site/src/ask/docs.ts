/**
 * Ask AI's cards: the docs assistant (backend/docs_ai) sends `CUSTOM docs_card` events, this plugin draws them in
 * <agui-chat>. Follow-up questions are the widget's own quick replies (`CUSTOM suggestions`).
 *
 *   code    code quoted verbatim from the docs; several blocks are tabs; Copy; where it comes from
 *   pages   where it is documented: a row per page, the whole row opens it
 *   steps   a numbered how-to, each step with an optional code block
 *   live    a real card from the card gallery, playing in the answer
 */
import { h, defineTheme } from '../../../packages/agui-chat/src/index'
import type { AguiChatElement } from '../../../packages/agui-chat/src/element'
import type { AguiEvent, ChatApi, Plugin } from '../../../packages/agui-chat/src/types'

interface Block { id: string; lang: string; label: string; code: string; url: string; page: string; section: string }
interface PageRef { url: string; title: string; group?: string; section?: string; description?: string }
type Card =
  | { kind: 'code'; caption?: string; blocks: Block[] }
  | { kind: 'pages'; pages: PageRef[] }
  | { kind: 'steps'; title?: string; steps: { text: string; block?: Block }[] }
  | { kind: 'live'; specimen: string; about?: string }

const GALLERY = `${import.meta.env.BASE_URL.replace(/\/?$/, '/')}frontend/card-gallery/`
const ICON_COPY = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="2"/><path d="M10.5 5.5V4a1.5 1.5 0 0 0-1.5-1.5H4A1.5 1.5 0 0 0 2.5 4v5A1.5 1.5 0 0 0 4 10.5h1.5"/></svg>'
const ICON_DOC = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1.75h5.25L12.5 5v9.25H4z"/><path d="M9 1.75V5.25h3.5M6 8.25h4.5M6 10.75h3"/></svg>'
const CHEVRON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5 10.5 8 6 12.5"/></svg>'

const icon = (svg: string, cls = 'dc-i') => { const s = h('span', { class: cls, 'aria-hidden': 'true' }); s.innerHTML = svg; return s }
const inline = (text: string) => {
  const span = h('span')
  for (const [i, part] of text.split('`').entries()) span.append(i % 2 ? h('code', null, part) : part)
  return span
}

function copyButton(get: () => string): HTMLButtonElement {
  const label = h('span', null, 'Copy')
  const b = h('button', { class: 'dc-copy', type: 'button', 'data-keep': true, onclick: async () => {
    try { await navigator.clipboard.writeText(get()); label.textContent = 'Copied' } catch { label.textContent = 'Select and copy' }
    b.classList.add('done')
    setTimeout(() => { label.textContent = 'Copy'; b.classList.remove('done') }, 1600)
  } }, icon(ICON_COPY), label) as HTMLButtonElement
  return b
}

function codeCard(c: Extract<Card, { kind: 'code' }>): HTMLElement {
  let current = 0
  const pre = h('pre', null, h('code'))
  const from = h('a', { class: 'dc-from', target: '_blank', rel: 'noopener' })
  const show = (i: number) => {
    current = i
    const b = c.blocks[i]
    pre.firstElementChild!.textContent = b.code
    from.href = b.url
    from.replaceChildren(icon(ICON_DOC), h('span', null, `${b.page}${b.section && b.section !== b.page ? ` · ${b.section}` : ''}`))
    tabs?.querySelectorAll('button').forEach((t, n) => t.setAttribute('aria-selected', String(n === i)))
  }
  const tabs = c.blocks.length > 1 ? h('div', { class: 'dc-tabs', role: 'tablist' },
    c.blocks.map((b, i) => h('button', { type: 'button', role: 'tab', 'data-keep': true, onclick: () => show(i) }, b.label || b.lang))) : null
  const head = h('div', { class: 'dc-head' }, tabs ?? h('span', { class: 'dc-label' }, c.blocks[0].label || c.blocks[0].lang),
    copyButton(() => c.blocks[current].code))
  const el = h('div', { class: 'dc dc-code' }, c.caption ? h('div', { class: 'dc-cap' }, c.caption) : null, head, pre, from)
  show(0)
  return el
}

function pagesCard(c: Extract<Card, { kind: 'pages' }>): HTMLElement {
  return h('div', { class: 'dc dc-pages' }, c.pages.map((p) => h('a', { class: 'dc-page', href: p.url, target: '_blank', rel: 'noopener' },
    icon(ICON_DOC, 'dc-pi'),
    h('span', { class: 'dc-pt' }, p.group ? h('small', null, p.group) : null, h('b', null, p.section ? `${p.title} · ${p.section}` : p.title),
      p.description ? h('span', null, p.description) : null),
    icon(CHEVRON, 'dc-chev'))))
}

function stepsCard(c: Extract<Card, { kind: 'steps' }>): HTMLElement {
  return h('div', { class: 'dc dc-steps' }, c.title ? h('div', { class: 'dc-cap' }, c.title) : null,
    h('ol', null, c.steps.map((s, i) => h('li', null, h('span', { class: 'dc-n', 'aria-hidden': 'true' }, String(i + 1)),
      h('div', { class: 'dc-st' }, inline(s.text), s.block ? h('div', { class: 'dc-mini' },
        h('pre', null, h('code', null, s.block.code)), copyButton(() => s.block!.code)) : null)))))
}

function liveCard(c: Extract<Card, { kind: 'live' }>): HTMLElement {
  const stage = h('div', { class: 'dc-stage' })
  const replay = h('button', { class: 'dc-link', type: 'button', 'data-keep': true }, 'Replay') as HTMLButtonElement
  const el = h('div', { class: 'dc dc-live' }, stage,
    h('div', { class: 'dc-foot' }, h('span', null, c.about ?? ''), replay,
      h('a', { class: 'dc-link', href: `${GALLERY}#${c.specimen}`, target: '_blank', rel: 'noopener' }, 'All cards')))
  void (async () => {   // the gallery's specimen, in a small chat of its own
    const [{ SPECIMENS, playSpecimen }, { formguide }] = await Promise.all([
      import('../demo/gallery'), import('../../../packages/agui-chat/src/formguide/index')])
    const s = SPECIMENS.find((x) => x.id === c.specimen)
    if (!s) { el.remove(); return }
    const mini = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', 'persist-thread': 'off', attach: 'off', typing: 'plain', lang: 'en', 'quick-replies': 'off' })) mini.setAttribute(k, v)
    const host = el.getRootNode() instanceof ShadowRoot ? (el.getRootNode() as ShadowRoot).host : null
    mini.setAttribute('scheme', host?.getAttribute('scheme') || 'auto')
    stage.append(mini)
    const play = playSpecimen(mini, s, formguide)
    replay.addEventListener('click', () => play.replay())
  })()
  return el
}

export function docs(): Plugin {
  return {
    name: 'docs',
    toolLabels: { search_docs: 'Searching the docs' },
    onEvent(ev: AguiEvent, chat: ChatApi) {
      if (ev.type !== 'CUSTOM' || ev.name !== 'docs_card') return false
      const c = ev.value as Card
      const el = c?.kind === 'code' && c.blocks?.length ? codeCard(c)
        : c?.kind === 'pages' && c.pages?.length ? pagesCard(c)
        : c?.kind === 'steps' && c.steps?.length ? stepsCard(c)
        : c?.kind === 'live' ? liveCard(c) : null
      if (el) chat.append(el)
      return true
    },
  }
}

/** The docs theme: the default look plus the cards above, from the widget's tokens (light and dark follow). */
defineTheme('docs', {
  css: `
.dc { margin: 10px 0 12px; border-radius: var(--agui-radius); background: var(--agui-soft); color: var(--agui-ink); overflow: hidden;
  animation: dc-in .2s var(--agui-ease, ease-out) both; }
/* the widget's quick replies pull up under a bubble (margin-top: -8px); after a card they keep the card rhythm */
.dc + .quick { margin-top: 4px; }
@keyframes dc-in { from { opacity: 0; transform: translateY(4px); } }
@media (prefers-reduced-motion: reduce) { .dc { animation: none; } }
.dc-cap { padding: 12px 14px 0; font-size: 13px; font-weight: 600; color: var(--agui-ink-2); }
.dc-i, .dc-pi, .dc-chev { display: inline-flex; flex: none; }
.dc-i svg, .dc-pi svg, .dc-chev svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }

.dc-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 8px 0 14px; min-height: 40px; }
.dc-label { font-size: 12px; font-weight: 600; color: var(--agui-ink-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dc-tabs { display: flex; gap: 2px; padding: 2px; border-radius: var(--agui-radius-pill); background: var(--agui-bg); overflow-x: auto; scrollbar-width: none; margin-left: -8px; }
.dc-tabs::-webkit-scrollbar { display: none; }
.dc-tabs button { flex: none; border: 0; background: none; color: var(--agui-ink-2); font: 500 12px/1 var(--agui-font); padding: 7px 11px;
  border-radius: var(--agui-radius-pill); cursor: pointer; transition: background .18s, color .18s; white-space: nowrap; }
.dc-tabs button[aria-selected=true] { background: var(--agui-surface); color: var(--agui-ink); box-shadow: 0 1px 2px color-mix(in srgb, var(--agui-ink) 12%, transparent); }
.dc-copy { flex: none; display: inline-flex; align-items: center; gap: 5px; border: 0; border-radius: var(--agui-radius-pill); background: var(--agui-bg);
  color: var(--agui-ink-2); font: 500 12px/1 var(--agui-font); padding: 7px 11px; min-height: 30px; cursor: pointer; transition: color .18s, background .18s; }
.dc-copy:hover { color: var(--agui-ink); }
.dc-copy.done { color: var(--agui-ok); }
.dc-code pre, .dc-mini pre { margin: 0; padding: 10px 14px 12px; overflow-x: auto; font: 13px/1.6 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.dc-code code, .dc-mini code { white-space: pre; background: none; padding: 0; }
.dc-from { display: flex; align-items: center; gap: 6px; padding: 9px 14px 11px; border-top: 1px solid var(--agui-line); font-size: 12px;
  color: var(--agui-ink-3); text-decoration: none; transition: color .18s; }
.dc-from:hover { color: var(--agui-link); }
.dc-from span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.dc-pages { display: flex; flex-direction: column; padding: 4px; gap: 2px; }
.dc-page { display: flex; align-items: center; gap: 12px; padding: 11px 12px; min-height: 52px; border-radius: calc(var(--agui-radius) - 4px);
  color: var(--agui-ink); text-decoration: none; transition: background .18s; }
.dc-page:hover { background: var(--agui-bg); }
.dc-page:focus-visible, .dc-tabs button:focus-visible, .dc-copy:focus-visible, .dc-link:focus-visible { outline: 2px solid var(--agui-accent); outline-offset: 1px; }
.dc-pi { width: 32px; height: 32px; border-radius: 10px; align-items: center; justify-content: center; background: var(--agui-bg); color: var(--agui-link); }
.dc-pt { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.dc-pt small { font-size: 11px; font-weight: 600; color: var(--agui-ink-3); text-transform: uppercase; letter-spacing: .04em; }
.dc-pt b { font-size: 14px; font-weight: 600; }
.dc-pt span { font-size: 12px; color: var(--agui-ink-3); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.dc-chev { color: var(--agui-ink-3); }

.dc-steps ol { list-style: none; margin: 0; padding: 10px 14px 12px; display: flex; flex-direction: column; gap: 12px; }
.dc-steps li { display: flex; gap: 12px; align-items: flex-start; }
.dc-n { flex: none; width: 24px; height: 24px; border-radius: 999px; background: var(--agui-accent); color: var(--agui-on-accent);
  font: 600 12px/24px var(--agui-font); text-align: center; }
.dc-st { flex: 1; min-width: 0; font-size: 14px; line-height: 1.5; padding-top: 2px; }
.dc-st code { font-size: 13px; background: var(--agui-bg); padding: 1px 5px; border-radius: 6px; }
.dc-mini { position: relative; margin-top: 8px; border-radius: 10px; background: var(--agui-bg); }
.dc-mini pre { padding: 10px 12px; padding-right: 84px; }
.dc-mini .dc-copy { position: absolute; top: 6px; right: 6px; background: var(--agui-soft); }

.dc-live { background: none; border: 1px solid var(--agui-line); }
.dc-stage { height: 380px; }
.dc-stage agui-chat { display: block; height: 100%; }
.dc-stage agui-chat::part(header), .dc-stage agui-chat::part(composer) { display: none; }
.dc-stage agui-chat::part(panel) { border: 0; box-shadow: none; border-radius: 0; }
.dc-foot { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-top: 1px solid var(--agui-line); font-size: 12px; color: var(--agui-ink-3); }
.dc-foot span { flex: 1; min-width: 0; }
.dc-link { border: 0; background: none; padding: 6px 2px; color: var(--agui-link); font: 500 12px var(--agui-font); cursor: pointer; text-decoration: none; }
@media (pointer: coarse) { .dc-copy, .dc-tabs button { min-height: 36px; } .dc-link { padding: 12px 4px; } }
`,
})

/** The tooltip's look, with the chat's tokens: a dark plate, its keys as small caps on the right. */
export const TIP_CSS = `.tip { position: absolute; z-index: 9; max-width: 260px; display: grid; gap: 4px; padding: 4px 8px; border-radius: var(--agui-radius-sm, 10px);
  background: var(--agui-ink); color: var(--agui-bg); font: 12px/1.3 var(--agui-font); pointer-events: none;
  box-shadow: 0 6px 18px -6px var(--agui-shadow); animation: tip-in .12s var(--agui-ease) both; }
.tip[hidden] { display: none; }
@keyframes tip-in { from { opacity: 0; transform: translateY(2px); } to { opacity: 1; transform: none; } }
.tip-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; white-space: nowrap; }
.tip-keys { display: inline-flex; gap: 3px; }
.tip kbd { min-width: 18px; padding: 1px 5px; border-radius: 6px; text-align: center; font: 500 11px/16px var(--agui-font);
  background: color-mix(in srgb, var(--agui-bg) 18%, transparent); color: inherit; }
:host(.dark) .tip { background: var(--agui-soft); color: var(--agui-ink); box-shadow: 0 6px 18px -6px var(--agui-shadow), 0 0 0 .5px var(--agui-line-2); }   /* dark grey, as macOS in dark */
:host(.dark) .tip kbd { background: color-mix(in srgb, var(--agui-ink) 14%, transparent); }
/* the + menu: a rounded plate over its button; rows of an icon, a label, keys or a chevron */
.menu { position: absolute; z-index: 8; min-width: 220px; max-width: min(320px, calc(100% - 16px)); overflow-y: auto; display: grid; padding: 6px; box-sizing: border-box;
  border-radius: var(--agui-menu-radius, 16px); background: var(--agui-menu-bg, var(--agui-bg)); color: var(--agui-ink);
  border: 1px solid var(--agui-line); box-shadow: 0 10px 30px -10px var(--agui-shadow); animation: tip-in .14s var(--agui-ease) both; transform-origin: bottom left; }
:host(.dark) .menu { background: var(--agui-menu-bg, var(--agui-soft)); border-color: var(--agui-line-2); }
.menu-i { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 36px; padding: 6px 10px; border: 0; border-radius: 10px; background: none; color: inherit;
  font: 15px/1.3 var(--agui-font); text-align: left; cursor: pointer; }
.menu-i:hover, .menu-i:focus-visible { background: var(--agui-soft); outline: none; }
:host(.dark) .menu-i:hover, :host(.dark) .menu-i:focus-visible { background: color-mix(in srgb, var(--agui-ink) 10%, transparent); }
.menu-i svg { flex: none; color: var(--agui-ink-2); }
.menu-l { flex: 1; min-width: 0; display: grid; }
.menu-h { font-size: 13px; color: var(--agui-ink-2); }
.menu-k { display: inline-flex; gap: 3px; color: var(--agui-ink-3); } .menu-k kbd { font: 13px var(--agui-font); }
.menu-c { display: grid; color: var(--agui-ink-3); } .menu-c svg { width: 16px; height: 16px; color: inherit; }
.menu-back { color: var(--agui-ink-2); font-size: 13px; font-weight: 600; margin-bottom: 2px; }
@media (hover: none) { .menu-i { min-height: 44px; font-size: 17px; } }
@media (prefers-reduced-motion: reduce) { .tip, .menu { animation: none; } }
/* source links under an answer: one row (it scrolls sideways and fades at its edge on a phone, wraps with a mouse);
   only a link that opens something is a filled pill with a document glyph */
:host { --agui-mark: color-mix(in srgb, #ffd60a 55%, transparent); }
:host(.dark) { --agui-mark: color-mix(in srgb, #ffd60a 34%, transparent); }
.srcs { display: flex; gap: 8px; flex-wrap: wrap; }
.src { flex: none; position: relative; display: inline-flex; align-items: center; gap: 6px; max-width: 240px; height: 32px; padding: 0; border: 0;
  background: none; color: var(--agui-ink-2); font: 13px var(--agui-font); }
.src svg { flex: none; }
.src b { font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
:is(button, a).src { padding: 0 12px 0 10px; text-decoration: none; border-radius: var(--agui-radius-pill); background: var(--agui-source-bg, var(--agui-soft)); cursor: pointer; transition: background .15s; }
:is(button, a).src b { font-weight: 500; color: var(--agui-ink); }
:is(button, a).src:hover { background: var(--agui-line-2); }
.src.on { color: var(--agui-link); }
.src.on, .src.on:hover { background: color-mix(in srgb, var(--agui-link) 14%, var(--agui-soft)); }
/* what a tap opens: a sheet from the bottom of the chat on a phone, a popover over the link with a mouse */
.src-veil { position: absolute; inset: 0; z-index: 7; background: var(--agui-scrim); animation: src-fade .2s ease both; }
.src-view { position: absolute; z-index: 8; box-sizing: border-box; outline: none; display: flex; flex-direction: column;
  background: var(--agui-sheet-bg, var(--agui-bg)); color: var(--agui-ink); font: 15px/1.5 var(--agui-font); }
:host(.dark) .src-view { background: var(--agui-sheet-bg, var(--agui-surface)); }
.src-body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 12px; }
.src-live { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
.src-sheet { left: 0; right: 0; bottom: 0; max-height: 80%; padding: 8px 20px max(20px, env(safe-area-inset-bottom)); border-radius: var(--agui-radius-lg) var(--agui-radius-lg) 0 0;
  animation: src-up .24s var(--agui-ease) both; transition: transform .2s var(--agui-ease); }
.src-sheet, .src-sheet:focus-visible { box-shadow: 0 -10px 40px -12px var(--agui-shadow); }   /* a sheet never wears the focus ring */
.src-sheet.drag { transition: none; }
.src-pop { width: min(380px, calc(100% - 16px)); max-height: min(440px, calc(100% - 16px)); padding: 16px; border-radius: var(--agui-menu-radius, 16px); border: 1px solid var(--agui-line);
  animation: tip-in .14s var(--agui-ease) both; }
.src-pop, .src-pop:focus-visible { box-shadow: 0 14px 40px -10px var(--agui-shadow); }
:host(.dark) .src-pop { background: var(--agui-sheet-bg, var(--agui-soft)); border-color: var(--agui-line-2); }
.src-view.out { transition: transform .16s cubic-bezier(.4, 0, 1, 1), opacity .16s; }
.src-sheet.out { transform: translateY(100%) !important; }
.src-pop.out, .src-veil.out { opacity: 0; transition: opacity .16s; }
.src-grab { position: relative; align-self: center; flex: none; width: 36px; height: 5px; border-radius: 3px; background: color-mix(in srgb, var(--agui-ink) 22%, transparent); touch-action: none; }
.src-grab::after { content: ''; position: absolute; inset: -10px -150px -6px; }
.src-head { flex: none; display: flex; align-items: flex-start; gap: 12px; touch-action: none; }
.src-head > div { flex: 1; min-width: 0; }
.src-head b, .src-head small { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; overflow-wrap: anywhere; }
.src-head b { font: 600 17px/1.3 var(--agui-font); }
.src-head small { margin-top: 2px; color: var(--agui-ink-2); font-size: 13px; line-height: 1.35; }
.src-pop .src-head b { font-size: 15px; }
.src-x { flex: none; position: relative; width: 30px; height: 30px; border: 0; border-radius: 50%; display: grid; place-items: center; cursor: pointer;
  background: var(--agui-soft); color: var(--agui-ink-2); }
.src-x::after { content: ''; position: absolute; inset: -7px; }
:host(.dark) .src-x, :host(.dark) .src-pop .src-go:not(:disabled):hover { background: color-mix(in srgb, var(--agui-ink) 12%, transparent); }
.src-text { flex: 1 1 auto; min-height: 5.5em; overflow-y: auto; overscroll-behavior: contain; white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.5; color: var(--agui-ink-2); }
.src-text mark { background: var(--agui-mark-bg, var(--agui-mark)); color: var(--agui-ink); border-radius: 3px; padding: 1px 0;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.src-foot { flex: none; display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 32px; }
.src-foot .btn { margin-left: auto; text-decoration: none; }
.src-pop .src-foot .btn { margin-right: -6px; }
.src-sheet .src-foot { min-height: 44px; }
.src-sheet .btn { min-height: 44px; padding: 0 18px; font-size: 15px; display: inline-flex; align-items: center; }
.src-pager { display: flex; align-items: center; gap: 2px; margin-left: -14px; color: var(--agui-ink-2); font-size: 13px; font-variant-numeric: tabular-nums; }
.src-go { width: 32px; height: 32px; border: 0; border-radius: 50%; background: none; color: inherit; display: grid; place-items: center; cursor: pointer; }
.src-go:disabled { opacity: .35; cursor: default; }
.src-go:not(:disabled):hover { background: var(--agui-soft); }
@keyframes src-up { from { transform: translateY(100%); } }
@keyframes src-fade { from { opacity: 0; } }
@media (hover: none) {
  .srcs { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent); mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent); }
  .srcs::-webkit-scrollbar { display: none; }
  .src:last-child { margin-right: 28px; }
  :is(button, a).src::after { content: ''; position: absolute; inset: -6px 0; }
  .src-go { width: 44px; height: 44px; } .src-pager { margin-left: -20px; }
}
@media (prefers-reduced-motion: reduce) { .src-veil, .src-view { animation: none; transition: none; } }`


const styled = new WeakSet<Node>()
/** The tooltip's, the menu's and the sources' styles in the root they show in (a shadow root gets them once; the page needs a <style> of its own). */
export function adoptTipCss(host: HTMLElement): void {
  const root = host.getRootNode()
  if (styled.has(root) || !(root instanceof ShadowRoot)) return
  styled.add(root)
  try { const sh = new CSSStyleSheet(); sh.replaceSync(TIP_CSS); root.adoptedStyleSheets = [...root.adoptedStyleSheets, sh] }
  catch { const el = document.createElement('style'); el.textContent = TIP_CSS; root.append(el) }
}

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
@media (prefers-reduced-motion: reduce) { .tip, .menu { animation: none; } }`


const styled = new WeakSet<Node>()
/** The tooltip's and the menu's styles in the root they show in (a shadow root gets them once; the page needs a <style> of its own). */
export function adoptTipCss(host: HTMLElement): void {
  const root = host.getRootNode()
  if (styled.has(root) || !(root instanceof ShadowRoot)) return
  styled.add(root)
  try { const sh = new CSSStyleSheet(); sh.replaceSync(TIP_CSS); root.adoptedStyleSheets = [...root.adoptedStyleSheets, sh] }
  catch { const el = document.createElement('style'); el.textContent = TIP_CSS; root.append(el) }
}

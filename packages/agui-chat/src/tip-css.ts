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
@media (prefers-reduced-motion: reduce) { .tip { animation: none; } }`

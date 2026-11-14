/** The card blocks' styles: they ship with the blocks (agui-chat.blocks.js in the one-script build) and are added to
 *  each chat's shadow root the first time a card from blocks lands there, before the theme so the theme still wins. */
export const BLOCKS_CSS = `
/* cards from blocks (formguide/blocks.ts): small parts, one look; colours only from the theme and a tone */
.bk { display: grid; gap: 12px; }
.bk .card-q, .bk .acts { margin: 0; }
.bk-title .muted, .bk-note, .bk-small { font-size: 13px; }
.bk-strong { font-weight: 600; font-size: 17px; letter-spacing: -0.01em; }
.bk-list { border: 1px solid var(--agui-option-border, var(--agui-line)); border-radius: var(--agui-radius-sm); background: var(--agui-option-bg, var(--agui-bg)); overflow: hidden; }
.bk-row { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 10px 12px; }
.bk-row + .bk-row { border-top: 1px solid var(--agui-line); }
.bk-label { flex: 1; min-width: 0; color: var(--agui-ink-2); }
.bk-value { font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
.bk-row.tone-ok .bk-value, .bk-row.tone-danger .bk-value, .bk-row.tone-accent .bk-value { color: inherit; } .bk-row[class*=tone-] .bk-label { color: var(--agui-ink-2); }
.bk-img { display: block; width: 100%; object-fit: cover; border-radius: var(--agui-radius-sm); background: var(--agui-soft); }
.bk-place { display: flex; align-items: center; gap: 12px; }
.bk-place > img, .bk-avatar { width: 52px; height: 52px; flex: none; border-radius: 12px; object-fit: cover; background: var(--agui-soft); }
.bk-avatar { display: grid; place-items: center; font-size: 20px; font-weight: 700; color: var(--agui-ink-2); }
.bk-place-t { flex: 1; min-width: 0; }
.bk-rating { font-weight: 600; font-variant-numeric: tabular-nums; }
.bk-big { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; font-variant-numeric: tabular-nums; }
.bk-stat.tone-ok .bk-big, .bk-stat.tone-danger .bk-big, .bk-stat.tone-accent .bk-big { color: inherit; } .bk-stat[class*=tone-] .muted { color: var(--agui-ink-2); }
.bk-arrow { margin: 0 8px; color: var(--agui-ink-3); }
.bk-steps ul { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 10px; }
.bk-steps li { display: flex; align-items: center; gap: 10px; }
.bk-steps li.done { color: var(--agui-ink-2); }
.bk-check { width: 22px; height: 22px; flex: none; border-radius: 50%; border: 1.5px solid var(--agui-line-2); display: grid; place-items: center; }
.bk-steps li.done .bk-check { background: var(--agui-ok); border-color: var(--agui-ok); color: var(--agui-on-ok); }
.bk-check .bk-ico, .bk-check .bk-ico svg { width: 14px; height: 14px; }   /* more specific than .bk-ico svg below */
.bk-bar { height: 6px; margin-top: 6px; border-radius: var(--agui-radius-pill); background: var(--agui-soft); overflow: hidden; }
.bk-bar > i { display: block; height: 100%; background: var(--agui-link); border-radius: inherit; transition: width .3s var(--agui-ease); }
.bk-swatches { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 8px; }
.bk-sw { display: grid; gap: 6px; padding: 8px; border: 1px solid var(--agui-line-2); border-radius: var(--agui-radius-sm); background: var(--agui-option-bg, var(--agui-bg));
  color: inherit; font: inherit; text-align: left; cursor: pointer; transition: transform .12s, border-color .15s; }
.bk-sw:active { transform: scale(.97); }
.bk-sw.on { border-color: var(--agui-link); box-shadow: inset 0 0 0 1px var(--agui-link); }   /* chosen: a solid 2 px edge */
.bk-sw:focus-visible { box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 35%, transparent); }
.bk-sw.on:focus-visible { box-shadow: inset 0 0 0 1px var(--agui-link), 0 0 0 3px color-mix(in srgb, var(--agui-link) 35%, transparent); }
@media (hover: hover) { .bk-sw:not(.on):hover { border-color: var(--agui-ink-3); } }
.bk-sw-c { display: flex; height: 28px; border-radius: 6px; overflow: hidden; }
.bk-sw-c > i { flex: 1; }
.bk-group { display: grid; gap: 8px; }
.bk-cap { font-size: 13px; font-weight: 600; color: var(--agui-ink-2); }
.bk .chips { row-gap: 8px; }
.chip.bk-more { border-style: dashed; color: var(--agui-link); }
.bk-empty { display: flex; align-items: center; min-height: 34px; font-size: 13px; color: var(--agui-ink-2); }
@media (pointer: coarse) { .bk-empty { min-height: 44px; } }
.bk-submit { display: grid; gap: 8px; }
.bk-hours { display: grid; gap: 12px; }
.bk-pair { display: grid; gap: 8px; }
.bk-pair .chip { min-width: 44px; }
.bk-times { display: flex; align-items: center; gap: 8px; }
.bk-times .text-in { width: auto; flex: 1; min-width: 0; margin-top: 0; }
.bk-add { justify-self: start; }
.bk-preview { position: relative; display: block; overflow: hidden; aspect-ratio: 16 / 10; border-radius: var(--agui-radius-sm); border: 1px solid var(--agui-line); background: var(--agui-soft); }
.bk-preview:focus-visible { outline: none; box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 35%, transparent); }
.bk-preview.tall { aspect-ratio: 9 / 16; max-width: 220px; justify-self: center; width: 100%; }
.bk-preview iframe { position: absolute; top: 0; left: 0; border: 0; transform-origin: 0 0; pointer-events: none; background: white; }
.bk-need { font-size: 13px; line-height: 16px; min-height: 16px; }   /* its place is kept: the button never moves */
.bk-cal + .bk-link, .bk-link + .bk-cal, .bk-cal + .bk-cal { border-top: 1px solid var(--agui-line); }
.bk-menu .bk-link { padding-left: 42px; border-top: 1px solid var(--agui-line); }
.bk-chart { display: grid; gap: 10px; min-width: 0; }
.bk-chart-t .bk-small { margin-top: 2px; }
.bk-canvas { position: relative; min-width: 0; }
.bk-canvas canvas { display: block; }
.bk-legend { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 12px; color: var(--agui-ink-2); }
.bk-legend span { display: inline-flex; align-items: center; gap: 6px; }
.bk-legend i { width: 9px; height: 9px; border-radius: 2px; flex: none; }
.bk-data summary { font-size: 12px; color: var(--agui-ink-2); cursor: pointer; width: max-content; }
.bk-data table { width: 100%; margin-top: 6px; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
.bk-data th, .bk-data td { padding: 4px 0; text-align: right; border-top: 1px solid var(--agui-line); font-weight: 400; }
.bk-data th[scope=row] { text-align: left; color: var(--agui-ink-2); }
.bk-barlist { display: grid; gap: 10px; }
.bk-bl-t { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; color: var(--agui-ink-2); }
.bk-num { font-variant-numeric: tabular-nums; color: var(--agui-ink); }
.bk-track { height: 6px; margin-top: 4px; border-radius: var(--agui-radius-pill); background: var(--agui-soft); overflow: hidden; }
.bk-track > i { display: block; height: 100%; border-radius: inherit; background: var(--agui-link); }
.bk-stack { display: flex; gap: 2px; height: 12px; }
.bk-stack > i { min-width: 2px; }
.bk-stack > i:first-child { border-radius: 4px 0 0 4px; } .bk-stack > i:last-child { border-radius: 0 4px 4px 0; } .bk-stack > i:only-child { border-radius: 4px; }
.bk-meter { position: relative; height: 8px; border-radius: var(--agui-radius-pill); background: var(--agui-soft); }
.bk-meter > i { display: block; height: 100%; border-radius: inherit; background: var(--agui-link); }
.bk-meter.over > i { background: var(--agui-danger); }
.bk-meter > b { position: absolute; top: -3px; bottom: -3px; width: 2px; margin-left: -1px; border-radius: 1px; background: var(--agui-ink-2); }
.bk-meter-l { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; font-variant-numeric: tabular-nums; }
.bk-empty { padding: 12px 0; text-align: center; }
.bk-change { font-size: 13px; font-weight: 600; margin-top: 2px; }
.bk-change.tone-ok { color: var(--agui-ok); } .bk-change.tone-danger { color: var(--agui-danger); }
.bk-spark { display: block; width: 100%; height: 36px; margin-top: 8px; }
.bk-spark .l { fill: none; stroke: var(--agui-link); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; vector-effect: non-scaling-stroke; }
.bk-spark .a { fill: color-mix(in srgb, var(--agui-link) 10%, transparent); }
.bk-field { display: grid; gap: 4px; }
.bk-field .text-in { margin-top: 0; }
.bk-links { display: grid; border: 1px solid var(--agui-option-border, var(--agui-line)); border-radius: var(--agui-radius-sm); background: var(--agui-option-bg, var(--agui-bg)); overflow: hidden; }
.bk-link { display: flex; align-items: center; gap: 10px; width: 100%; min-height: 44px; padding: 0 12px; color: var(--agui-link); text-decoration: none; background: none; border: 0;
  font: inherit; text-align: left; cursor: pointer; }
.bk-link + .bk-link { border-top: 1px solid var(--agui-line); }
/* a row of the grouped list: its highlight and its focus fill the whole row (a button would shrink to its text); the
   focus ring is drawn inside, so the list's rounded, clipped edge never cuts it into side stripes */
.bk-link:active, .bk-link[aria-expanded=true] { background: var(--agui-soft); }
@media (hover: hover) { .bk-link:hover { background: var(--agui-soft); } }
.bk-link:focus-visible { box-shadow: inset 0 0 0 2px color-mix(in srgb, var(--agui-link) 55%, transparent); }
.bk-cal { display: grid; }
.bk-link.done { color: var(--agui-ok); }
.bk-ico { width: 20px; height: 20px; flex: none; display: grid; place-items: center; } .bk-ico svg { width: 20px; height: 20px; }
.bk-row .bk-ico { color: var(--agui-ink-3); }
.bk-hr { border: 0; border-top: 1px solid var(--agui-line); margin: 0; }
`

/** The card blocks' styles: they ship with the blocks (agui-chat.blocks.js in the one-script build) and are added to
 *  each chat's shadow root the first time a card from blocks lands there, before the theme so the theme still wins. */
export const BLOCKS_CSS = `
:host { --agui-warn: #b25000; } :host(.dark) { --agui-warn: #ff9f0a; }   /* a threshold's mark (orange, as on iOS); a theme may set its own */
/* cards from blocks (formguide/blocks.ts): small parts, one look; colours only from the theme and a tone */
.bk { display: grid; gap: 12px; }
.bk .card-q, .bk .acts { margin: 0; }
.bk-title .muted, .bk-note, .bk-small { font-size: 13px; }
.bk-strong { font-weight: 600; font-size: 17px; letter-spacing: -0.01em; }
.bk-list { border: 1px solid var(--agui-option-border, var(--agui-line)); border-radius: var(--agui-radius-sm); background: var(--agui-option-bg, var(--agui-bg)); overflow: hidden; }
.bk-row { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 10px 12px; }
.bk-row + .bk-row { border-top: 1px solid var(--agui-line); }
.bk-label { flex: 1; min-width: 0; color: var(--agui-ink-2); }
.bk-value { font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; min-width: 0; max-width: 65%; overflow-wrap: anywhere; }   /* a long value wraps, never over its label */
.bk-row.tone-ok .bk-value, .bk-row.tone-danger .bk-value, .bk-row.tone-accent .bk-value { color: inherit; } .bk-row[class*=tone-] .bk-label { color: var(--agui-ink-2); }
.bk-img { display: block; width: 100%; object-fit: cover; border-radius: var(--agui-radius-sm); background: var(--agui-soft); }
.bk-place { display: flex; align-items: center; gap: 12px; }
.bk-place > img, .bk-avatar { width: 52px; height: 52px; flex: none; border-radius: 12px; object-fit: cover; background: var(--agui-soft); }
.bk-place > img.tall { width: 39px; border-radius: 8px; box-shadow: 0 0 0 1px var(--agui-line); }   /* a page's thumbnail, 3:4 */
.bk-avatar { display: grid; place-items: center; font-size: 20px; font-weight: 700; color: var(--agui-ink-2); }
.bk-place-t { flex: 1; min-width: 0; }
.bk-rating { font-weight: 600; font-variant-numeric: tabular-nums; }
/* a choice as rows: a tile (photo, glyph or letter), the name, a second line, a chevron; hairlines between, inset to the text */
.bk-pick-l { display: grid; }
.bk-pick-row { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 60px; padding: 10px 0; border: 0; background: none; color: inherit;
  font: inherit; text-align: left; cursor: pointer; position: relative; border-radius: var(--agui-radius-sm); -webkit-tap-highlight-color: transparent; }
.bk-pick-row + .bk-pick-row::before { content: ''; position: absolute; top: 0; left: 56px; right: 0; height: 1px; background: var(--agui-line); }
.bk-pick-row:not(:disabled):active { background: var(--agui-soft); }
@media (hover: hover) { .bk-pick-row:not(:disabled):hover { background: var(--agui-soft); box-shadow: 0 0 0 6px var(--agui-soft); } }
.bk-pick-row:disabled { cursor: default; }
.bk-pick-i { width: 44px; height: 44px; flex: none; border-radius: 10px; object-fit: cover; background: var(--agui-soft); display: grid; place-items: center;
  font-size: 17px; font-weight: 600; color: var(--agui-ink-2); }
.bk-pick-t { flex: 1; min-width: 0; display: grid; gap: 1px; overflow-wrap: anywhere; }
.bk-pick-n { font-size: 17px; font-weight: 500; line-height: 1.3; letter-spacing: -0.01em; }
.bk-pick-t .muted { font-size: 14px; line-height: 1.35; }
.bk-pick-row > .bk-ico { flex: none; color: var(--agui-ink-3); }
.bk-pick-row > .ok-line { flex: none; margin: 0; }
.bk-pick-none { display: block; margin: 6px 0 -4px; padding: 10px 0; min-height: 44px; border: 0; background: none; color: var(--agui-ink-2); font: inherit; font-size: 16px; cursor: pointer; text-align: left; }
.bk-pick-none:hover { color: var(--agui-ink); }
.bk-title + .bk-pick { margin-top: 4px; }
/* an answered card: its title or place, then the result line, the same 12 px apart as a question card's */
.bk-title + .ok-line, .bk-place + .ok-line { margin-top: 12px; }
.bk-big { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; font-variant-numeric: tabular-nums; }
.bk-stat.tone-ok .bk-big, .bk-stat.tone-danger .bk-big, .bk-stat.tone-accent .bk-big { color: inherit; } .bk-stat[class*=tone-] .muted { color: var(--agui-ink-2); }
.bk-arrow { margin: 0 8px; color: var(--agui-ink-3); }
.bk-diff.inline { display: flex; align-items: flex-start; gap: 10px; font-size: 14px; line-height: 1.3; }
.bk-diff.inline b { font-weight: 600; }
.bk-note.ico { display: flex; align-items: flex-start; gap: 10px; }
.bk-note.ico > .bk-ico, .bk-diff.inline > .bk-ico { margin-top: -1px; }
.bk-diff.inline .bk-arrow { margin: 0 4px; }
.bk-diff .bk-ico { color: var(--agui-ink-3); }
.bk-diff .bk-small > .bk-ico { display: inline-grid; vertical-align: -4px; margin-right: 6px; }
.bk-diff + .bk-diff { margin-top: 8px; } .bk-diff.inline + .bk-diff.inline, .bk-note.ico + .bk-note.ico { margin-top: -4px; }
/* tiles: two or three tall pictures side by side, a name under each and a grey line; the chosen one is ringed with a tick */
.bk-tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 12px 10px; }
.bk-tile { position: relative; display: grid; gap: 6px; align-content: start; padding: 0; border: 0; background: none; color: inherit; font: inherit; text-align: left; cursor: pointer; min-width: 0; }
.bk-tile:disabled { cursor: default; }
.bk-tile-i { position: relative; display: grid; place-items: center; width: 100%; max-height: var(--agui-tile-h, 160px); overflow: hidden; border-radius: 12px;
  background: var(--agui-soft); color: var(--agui-ink-3); font-size: 22px; font-weight: 600; box-shadow: 0 0 0 1px var(--agui-line); transition: box-shadow .15s; }
.bk-tile-i > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: top; }
.bk-tile[aria-pressed=true] .bk-tile-i { box-shadow: 0 0 0 2px var(--agui-ink); }
.bk-tile[aria-pressed=true] .bk-tile-i::after { content: '\\2713'; position: absolute; top: 6px; right: 6px; width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center;
  background: var(--agui-ink); color: var(--agui-bg); font-size: 12px; font-weight: 700; }
@media (hover: hover) { .bk-tile:not(:disabled):hover .bk-tile-i { box-shadow: 0 0 0 2px var(--agui-line-2); } .bk-tile[aria-pressed=true]:not(:disabled):hover .bk-tile-i { box-shadow: 0 0 0 2px var(--agui-ink); } }
.bk-tile:focus-visible { outline: none; } .bk-tile:focus-visible .bk-tile-i { box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 45%, transparent); }
.bk-tile-n { font-size: 14px; font-weight: 500; line-height: 1.25; overflow-wrap: anywhere; }
.bk-tile-s { display: flex; gap: 4px; align-items: flex-start; font-size: 12px; line-height: 1.3; overflow-wrap: anywhere; }
.bk-tile-s .bk-ico, .bk-tile-s .bk-ico svg { width: 14px; height: 14px; margin-top: 1px; }
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
.bk-off { color: inherit; }   /* the reason sits in the chip's own quiet ink */
/* what to pick first, in the place (and height) of the chips that follow it */
.bk-first { display: flex; align-items: center; min-height: calc(13px * 1.2 + 18px);   /* a chip: its line, 8 px padding twice, its 1 px border */ font-size: 13px; color: var(--agui-ink-2); }
@media (pointer: coarse) { .bk-first { min-height: 44px; } }
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
.bk-track:has(> b) { position: relative; overflow: visible; } .bk-track > b { position: absolute; top: -3px; bottom: -3px; width: 2px; margin-left: -1px; border-radius: 1px; background: var(--agui-warn); }
.bk-barlist.ink .bk-track > i { background: var(--agui-ink); }
/* a timeline: a mark in a small circle, a title and a grey line, the time on the right; hairlines between */
.bk-tl { list-style: none; margin: 0; padding: 0; }
.bk-tl-i { display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; gap: 10px; align-items: start; padding: 8px 0; }
.bk-tl-i + .bk-tl-i { border-top: 1px solid var(--agui-line); }
.bk-tl-m { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; background: var(--agui-soft); color: var(--agui-ink-2); font-size: 11px; font-weight: 600; }
.bk-tl-i.tone-ok .bk-tl-m { background: color-mix(in srgb, var(--agui-ok) 20%, transparent); color: var(--agui-ok-ink, var(--agui-ink)); }
.bk-tl-t { display: grid; gap: 1px; min-width: 0; font-size: 14px; overflow-wrap: anywhere; }
.bk-tl-t > .bk-strong { font-size: 14px; color: var(--agui-ink); }   /* the tone shows in the mark only */
.bk-tl-ms { white-space: nowrap; font-variant-numeric: tabular-nums; }
.bk-tl-i > .bk-tl-t > .bk-barlist, .bk-tl-t .bk-chart { margin-top: 6px; }
/* more for a developer: a line that opens what is under it */
.bk-details-l { display: inline-flex; gap: 6px; align-items: center; min-height: 32px; padding: 0; border: 0; background: none; color: var(--agui-ink-2); font: inherit; font-size: 13px; cursor: pointer; }
.bk-details-l .chev { transition: transform .2s; } .bk-details-l[aria-expanded=true] .chev { transform: rotate(90deg); }
@media (pointer: coarse) { .bk-details-l { min-height: 44px; } }
.bk-details-b { display: grid; gap: 12px; padding-top: 4px; }
.bk-code { margin: 0; padding: 10px 12px; border-radius: var(--agui-radius-sm); background: var(--agui-soft); font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--agui-ink); }
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

/* the month grid, a range's value row and the review card's marks: drawn by the on-demand file only (month.ts, typed.ts, review.ts) */
.cal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.cal-title { border: 0; background: none; font: 600 15px/1.2 var(--agui-font); color: var(--agui-ink); padding: 6px 8px; border-radius: var(--agui-radius-sm);
  cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
.cal-title:hover { background: var(--agui-soft); }
.cal-caret { color: var(--agui-link); font-weight: 600; transition: transform .2s; }
.cal[data-mode=years] .cal-caret, .cal[data-mode=months] .cal-caret { transform: rotate(90deg); }
.cal-navs { display: inline-flex; gap: 2px; }
.cal-nav { width: 36px; height: 36px; border: 0; border-radius: var(--agui-radius-pill); background: none; color: var(--agui-link); cursor: pointer;
  display: grid; place-items: center; }
.cal-nav:hover { background: var(--agui-soft); }
.cal-nav:disabled { color: var(--agui-ink-3); opacity: .5; cursor: default; background: none; }
.cal-nav svg { width: 14px; height: 14px; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; text-align: center; }
.cal-wd { font-size: 11px; font-weight: 600; color: var(--agui-ink-2); padding: 4px 0; }
.cal-d { aspect-ratio: 1; max-height: 40px; border: 0; border-radius: var(--agui-radius-pill); background: none; color: var(--agui-ink); font: 15px/1 var(--agui-font);
  cursor: pointer; display: grid; place-items: center; transition: background .15s; }
.cal-d:hover { background: var(--agui-soft); }
.cal-d.today { color: var(--agui-link); font-weight: 600; }
.cal-d.on { background: var(--agui-calendar-on-bg, var(--agui-accent)); color: var(--agui-calendar-on-ink, var(--agui-on-accent)); font-weight: 600; }
.cal-d:disabled { color: var(--agui-ink-3); opacity: .45; cursor: default; background: none; }
.cal-years { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.cal-y { min-height: 40px; border: 0; border-radius: var(--agui-radius-sm); background: var(--agui-soft); color: var(--agui-ink); font: 15px/1 var(--agui-font); cursor: pointer; }
.cal-y.on { background: var(--agui-accent); color: var(--agui-on-accent); font-weight: 600; }
.cal-y:disabled { opacity: .4; cursor: default; }
.range-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.range-v { font-weight: 600; }
.range-p { font-size: 17px; font-weight: 600; }
.stepper .range-v { min-width: 44px; padding: 0 4px; text-align: center; font-size: 17px; font-variant-numeric: tabular-nums; }
.rev-s { cursor: pointer; align-items: center; }
.rev-s .dot { width: 14px; height: 14px; border: 1.5px dashed var(--agui-ink-3); border-radius: var(--agui-radius-pill); flex: none; }
.rev-s .okmark { width: 14px; color: var(--agui-ok); font-style: normal; font-weight: 700; flex: none; }
.row.issue .sev { width: 14px; font-style: normal; font-weight: 700; flex: none; color: var(--agui-ink-2); }
.row.issue.fixed .sev { color: var(--agui-ok); }
/* the calendar box, time slots, the slider and the stepper: drawn by the on-demand file only */
.cal { margin-top: 10px; border: 1px solid var(--agui-line); border-radius: var(--agui-radius); padding: 10px; background: var(--agui-bg); max-width: 340px; }
.range input[type=range] { appearance: none; -webkit-appearance: none; height: 28px; background: transparent; }
.range input[type=range]::-webkit-slider-runnable-track { height: 4px; border-radius: var(--agui-radius-pill);
  background: linear-gradient(to right, var(--agui-accent) var(--p, 50%), var(--agui-line-2) var(--p, 50%)); }
.range input[type=range]::-moz-range-track { height: 4px; border-radius: var(--agui-radius-pill); background: var(--agui-line-2); }
.range input[type=range]::-moz-range-progress { height: 4px; border-radius: var(--agui-radius-pill); background: var(--agui-accent); }
.range input[type=range][data-empty]::-moz-range-progress { background: transparent; }   /* no value yet: the track stays empty */
.range input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 26px; height: 26px; margin-top: -11px; border-radius: 50%;
  background: var(--agui-knob); border: 0.5px solid color-mix(in srgb, var(--agui-shadow) 40%, transparent); box-shadow: 0 2px 6px color-mix(in srgb, var(--agui-shadow) 60%, transparent); cursor: grab; }
.range input[type=range]::-moz-range-thumb { width: 26px; height: 26px; border-radius: 50%; background: var(--agui-knob); border: 0.5px solid color-mix(in srgb, var(--agui-shadow) 40%, transparent);
  box-shadow: 0 2px 6px color-mix(in srgb, var(--agui-shadow) 60%, transparent); cursor: grab; }
.strip .btn.link { margin-top: 6px; }
.slots { margin-top: 8px; }
.range input[type=range] { width: 100%; margin: 4px 0; }
.stepper { display: inline-flex; align-items: center; gap: 4px; }
.stepper .btn { width: 36px; height: 36px; min-height: 36px; padding: 0; display: grid; place-items: center; font-size: 17px; line-height: 1;
  border-radius: var(--agui-radius-pill); }
  .stepper .btn { width: 44px; height: 44px; }
`

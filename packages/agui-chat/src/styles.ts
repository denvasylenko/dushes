/**
 * The chat's styles, in its shadow root. The look and motion follow the Cheese project's chat
 * (Herefront AI, chat.css); every colour, radius and font is a token you can set on the element:
 *   agui-chat { --agui-accent: #0a7; --agui-radius: 6px; }
 * Themes (themes.ts) set the same tokens per scheme. Parts for deeper changes: panel, header, log, message, user, assistant, steps, card, chip, composer,
 * input, send, fab (e.g. agui-chat::part(card) { border-width: 2px }).
 */
export const CSS = `
:host { --agui-accent: #1d1d1f; --agui-on-accent: #fff; --agui-link: #0071e3; --agui-bg: #fff; --agui-surface: #fafafb;
  --agui-soft: #f2f2f5; --agui-ink: #1d1d1f; --agui-ink-2: #6e6e73; --agui-ink-3: #86868b; --agui-line: #ececf0;
  --agui-line-2: #e3e3e8; --agui-ok: #34c759; --agui-on-ok: #fff; --agui-danger: #ff3b30; --agui-on-danger: #fff;
  --agui-shadow: rgba(0,0,0,.3); --agui-scrim: rgba(0,0,0,.18); --agui-knob: #fff;
  --agui-radius: 14px; --agui-radius-sm: 10px; --agui-radius-lg: 20px; --agui-radius-pill: 999px; --agui-panel-width: 460px;
  --agui-font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Helvetica Neue", Arial, sans-serif;
  --agui-ease: cubic-bezier(.28, .11, .32, 1); --agui-fade: 450ms;
  display: block; font-family: var(--agui-font); color: var(--agui-ink); letter-spacing: -0.01em; }
:host([hidden]) { display: none; }
:host(.dark) { --agui-accent: #f5f5f7; --agui-on-accent: #1d1d1f; --agui-link: #4ea1ff; --agui-bg: #1c1c1e; --agui-surface: #242426;
  --agui-soft: #2c2c2e; --agui-ink: #f5f5f7; --agui-ink-2: #aeaeb2; --agui-ink-3: #8e8e93; --agui-line: #333336; --agui-line-2: #3a3a3c;
  --agui-shadow: rgba(0,0,0,.6); --agui-scrim: rgba(0,0,0,.4); }
* { box-sizing: border-box; }
[hidden] { display: none !important; }
button { font: inherit; color: inherit; }
button:focus, input:focus, [tabindex]:focus { outline: none; }
/* a soft ring for the keyboard only */
button:focus-visible, input:focus-visible, select:focus-visible, [tabindex]:focus-visible { outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 35%, transparent); }
.card:focus-visible { box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 22%, transparent); }

/* layout: floating (button + side panel), inline (fills its box), page (the whole window) */
.panel { display: flex; flex-direction: column; background: var(--agui-panel-bg, var(--agui-bg)); color: var(--agui-panel-ink, var(--agui-ink)); min-height: 0; text-align: left; }
.mode-inline { height: 100%; }
.mode-inline .panel { height: 100%; border: 1px solid var(--agui-line); border-radius: var(--agui-radius); overflow: hidden; }
.mode-page .panel { position: fixed; inset: 0; z-index: 2147483001; }   /* above the host page's own sticky bars */
.mode-page .log, .mode-page .foot { width: min(760px, 100%); margin: 0 auto; }
.mode-floating .panel { position: fixed; z-index: 2147483001; top: 0; right: 0; bottom: 0; width: min(var(--agui-panel-width), 100vw);
  box-shadow: -20px 0 60px -20px var(--agui-shadow); transform: translateX(104%); transition: transform .42s var(--agui-ease); visibility: hidden; }
.mode-floating.open .panel { transform: none; visibility: visible; }
.scrim { position: fixed; inset: 0; z-index: 2147483000; background: var(--agui-scrim); opacity: 0; pointer-events: none; transition: opacity .3s; }
.mode-floating.open .scrim { opacity: 1; pointer-events: auto; }
.mode-inline .scrim, .mode-page .scrim, .mode-inline .fab, .mode-page .fab { display: none; }
.fab { position: fixed; z-index: 2147482999; right: max(20px, env(safe-area-inset-right, 0px)); bottom: max(20px, env(safe-area-inset-bottom, 0px));
  display: flex; align-items: center; gap: 9px; border: 0; border-radius: var(--agui-radius-pill); padding: 13px 20px 13px 16px; cursor: pointer;
  background: var(--agui-accent); color: var(--agui-on-accent); font: 600 15px/1 var(--agui-font); box-shadow: 0 10px 30px -8px var(--agui-shadow);
  transform: translateY(20px); opacity: 0; transition: transform .35s var(--agui-ease), opacity .35s var(--agui-ease); }
.fab.show { transform: none; opacity: 1; }
.mode-floating.open .fab { opacity: 0; pointer-events: none; }
.fab svg, .spark { width: 18px; height: 18px; flex: none; }

/* header */
.head { display: flex; align-items: center; gap: 12px; padding: 14px 14px 12px 20px; border-bottom: 1px solid var(--agui-header-border, var(--agui-line));
  background: var(--agui-header-bg, transparent); color: var(--agui-header-ink, inherit); }
.logo { width: 32px; height: 32px; border-radius: var(--agui-radius-sm); flex: none; display: grid; place-items: center; background: var(--agui-accent); color: var(--agui-on-accent); }
.title { font-weight: 650; font-size: 15px; line-height: 1.2; }
.sub { font-size: 12px; color: var(--agui-ink-3); margin-top: 2px; }
.icon { flex: none; width: 36px; height: 36px; border: 0; border-radius: var(--agui-radius-sm); background: transparent; color: var(--agui-ink-2);
  display: grid; place-items: center; cursor: pointer; }
.head .icon:first-of-type { margin-left: auto; }
.icon:hover { background: var(--agui-soft); color: var(--agui-ink); }
.icon svg { width: 19px; height: 19px; }
.mode-inline .close, .mode-page .close { display: none; }

/* messages */
.log { flex: 1; overflow-y: auto; padding: 22px 20px 12px; background: var(--agui-log-bg, transparent); overscroll-behavior: contain; min-height: 0; }
.empty { padding: 22px 2px 10px; }
.empty h3 { font-size: 28px; line-height: 1.15; letter-spacing: -0.035em; margin: 0 0 8px; text-wrap: balance; }
.empty p { margin: 0 0 18px; color: var(--agui-ink-2); font-size: 15px; line-height: 1.45; }
.msg { margin: 0 0 20px; font-size: 15px; line-height: 1.58; letter-spacing: -0.008em; overflow-wrap: anywhere; }
.msg.me { display: flex; justify-content: flex-end; }
.msg.me > div { background: var(--agui-bubble-user-bg, var(--agui-soft)); color: var(--agui-bubble-user-ink, inherit); border-radius: var(--agui-bubble-radius, var(--agui-radius-lg)); padding: 10px 15px; max-width: 85%; white-space: pre-wrap; }
.msg.ai { color: var(--agui-bubble-ai-ink, inherit); }
.msg.ai p { margin: 0 0 10px; } .msg.ai p:last-child { margin-bottom: 0; }
.msg.ai ul { margin: 4px 0 10px; padding-left: 20px; } .msg.ai li { margin: 3px 0; }
.msg.ai a { color: var(--agui-link); }
.msg.ai code { font-size: .9em; background: var(--agui-soft); border-radius: var(--agui-radius-sm); padding: 1px 5px; }
.msg.ai .code { position: relative; margin: 8px 0 12px; background: var(--agui-soft); border-radius: var(--agui-radius-sm); overflow: hidden; }
.msg.ai .code pre { margin: 0; padding: 12px 14px; overflow-x: auto; font: 13px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0; }
.msg.ai .code code { background: none; padding: 0; font-size: inherit; white-space: pre; overflow-wrap: normal; }
.msg.ai .code[data-lang]::before { content: attr(data-lang); display: block; padding: 6px 14px 0; font-size: 11px; font-weight: 600; color: var(--agui-ink-3); text-transform: lowercase; }
.code-copy { position: absolute; top: 4px; right: 4px; border: 0; border-radius: var(--agui-radius-pill); background: var(--agui-bg); color: var(--agui-ink-2);
  font: 500 12px var(--agui-font); padding: 4px 10px; min-height: 28px; cursor: pointer; box-shadow: 0 0 0 1px var(--agui-line); }
.code-copy:hover { color: var(--agui-ink); }
.code-copy:focus-visible { outline: none; box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-accent) 30%, transparent), 0 0 0 1px var(--agui-accent); }
.notice { text-align: center; font-size: 12px; color: var(--agui-ink-3); margin: 0 0 16px; }
.error { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; color: var(--agui-danger); font-size: 13px; margin: 0 0 16px; }
.dots { display: inline-flex; gap: 4px; padding: 8px 0; }
.dots i { width: 7px; height: 7px; border-radius: var(--agui-radius-pill); background: var(--agui-ink-3); opacity: .5; animation: bounce 1.2s infinite; }
.dots i:nth-child(2) { animation-delay: .15s; } .dots i:nth-child(3) { animation-delay: .3s; }
@keyframes bounce { 0%, 60%, 100% { transform: none; opacity: .5; } 30% { transform: translateY(-4px); opacity: 1; } }
@keyframes pulse { 50% { opacity: .25; } }
/* streaming: every new word fades in (a negative delay continues the fade on a redraw) */
.w { animation: word var(--agui-fade) cubic-bezier(.2, .6, .3, 1) both; }
@keyframes word { from { opacity: 0; filter: blur(3px); } to { opacity: 1; filter: blur(0); } }

/* live tool steps */
.steps { margin: 0 0 14px; font-size: 13px; color: var(--agui-ink-3); }
.steps > button { display: inline-flex; align-items: center; gap: 6px; border: 0; background: none; padding: 2px 0; cursor: pointer; color: var(--agui-ink-3); }
.steps > button::after { content: "\\203A"; transition: transform .2s; } .steps.openlist > button::after { transform: rotate(90deg); }
.steps ul { list-style: none; margin: 6px 0 0; padding: 0; display: grid; gap: 7px; }
.steps.collapsed ul { display: none; }
.steps li { display: flex; align-items: center; gap: 9px; animation: rise .35s var(--agui-ease) both; }
.steps li ul { margin: 4px 0 0 25px; gap: 4px; } .steps li.has-sub { flex-wrap: wrap; } .steps li.has-sub > ul { flex-basis: 100%; }
.steps li .mark { width: 16px; height: 16px; border-radius: var(--agui-radius-pill); border: 2px solid var(--agui-line-2); flex: none; display: grid; place-items: center; }
.steps li.run .mark { border-color: var(--agui-line-2); border-top-color: var(--agui-link); animation: turn .8s linear infinite; }
.steps li.ok { color: var(--agui-ink-2); }
.steps li.ok .mark { border-color: var(--agui-ok); background: var(--agui-ok) center/10px no-repeat
  url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'%3E%3Cpath d='M2.5 6.2 5 8.6l4.5-5' fill='none' stroke='%23fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  animation: tick .3s both; }
.steps li.fail .mark { border-color: var(--agui-danger); background: var(--agui-danger); }
.steps li.sub .mark { width: 12px; height: 12px; border-width: 1.5px; background-size: 8px; }
@keyframes turn { to { transform: rotate(360deg); } }
@keyframes tick { from { transform: scale(.6); } to { transform: none; } }

/* hero: a landing's big field; the first message grows it into the chat (desktop) or a full-screen sheet (phone) */
.mode-hero .fab, .mode-hero .scrim, .mode-hero .close { display: none; }
.mode-hero .panel { background: transparent; }
.mode-hero:not(.open) .head, .mode-hero:not(.open) .log { display: none; }
.mode-hero:not(.open) .foot { padding: 0; background: none; }
.mode-hero:not(.open) .box { min-height: 60px; padding: 8px 8px 8px 16px; align-items: center; box-shadow: 0 10px 30px -14px var(--agui-shadow); }
.mode-hero:not(.open) textarea { font-size: 17px; }
.mode-hero.open .panel { background: var(--agui-panel-bg, var(--agui-bg)); border: 1px solid var(--agui-line); border-radius: var(--agui-radius-lg);
  overflow: hidden; animation: hero-grow .32s var(--agui-ease) both; }
.mode-hero.open .log { max-height: 70vh; min-height: 160px; }
.mode-hero.open .head { display: none; }
@keyframes hero-grow { from { opacity: .4; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@media (max-width: 759px) {
  .mode-hero.open .panel { position: fixed; inset: 0; z-index: 2147483001; border: 0; border-radius: 0; animation: hero-sheet .32s var(--agui-ease) both; }
  .mode-hero.open .head { display: flex; }
  .mode-hero.open .close { display: grid; }
  .mode-hero.open .log { max-height: none; flex: 1; }
  @keyframes hero-sheet { from { transform: translateY(24px); opacity: .6; } to { transform: none; opacity: 1; } }
}

/* cards inside the conversation */
.card { margin: 4px 0 20px; border: 1px solid var(--agui-card-border, var(--agui-line)); border-radius: var(--agui-card-radius, var(--agui-radius));
  background: var(--agui-card-bg, var(--agui-surface)); color: var(--agui-card-ink, inherit); padding: var(--agui-card-padding, 14px);
  -webkit-backdrop-filter: var(--agui-card-blur, none); backdrop-filter: var(--agui-card-blur, none);   /* glass: a translucent card-bg + blur */
  animation: rise .5s var(--agui-ease) both; font-size: 15px; line-height: 1.45; }
@keyframes rise { from { opacity: 0; transform: translateY(8px) scale(.98); } to { opacity: 1; transform: none; } }

/* cards from blocks (formguide/blocks.ts): small parts, one look; colours only from the theme and a tone */
.bk { display: grid; gap: 12px; }
.bk .card-q, .bk .acts { margin: 0; }
.bk-title .muted, .bk-note, .bk-small { font-size: 13px; }
.bk-strong { font-weight: 600; font-size: 17px; letter-spacing: -0.01em; }
.tone-accent { color: var(--agui-link); } .tone-ok { color: var(--agui-ok); } .tone-danger { color: var(--agui-danger); } .tone-muted { color: var(--agui-ink-3); }
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
.bk-sw.on { border-color: var(--agui-link); box-shadow: 0 0 0 2px color-mix(in srgb, var(--agui-link) 35%, transparent); }
.bk-sw-c { display: flex; height: 28px; border-radius: 6px; overflow: hidden; }
.bk-sw-c > i { flex: 1; }
.bk-field { display: grid; gap: 4px; }
.bk-field .text-in { margin-top: 0; }
.bk-links { display: grid; border: 1px solid var(--agui-option-border, var(--agui-line)); border-radius: var(--agui-radius-sm); background: var(--agui-option-bg, var(--agui-bg)); overflow: hidden; }
.bk-link { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 0 12px; color: var(--agui-link); text-decoration: none; background: none; border: 0;
  font: inherit; text-align: left; cursor: pointer; }
.bk-link + .bk-link { border-top: 1px solid var(--agui-line); }
.bk-link:active { background: var(--agui-soft); }
.bk-link.done { color: var(--agui-ok); }
.bk-ico { width: 20px; height: 20px; flex: none; display: grid; place-items: center; } .bk-ico svg { width: 20px; height: 20px; }
.bk-row .bk-ico { color: var(--agui-ink-3); }
.bk-hr { border: 0; border-top: 1px solid var(--agui-line); margin: 0; }
.card.done { opacity: .72; }
.chip input[type=checkbox] { accent-color: var(--agui-accent); width: 15px; height: 15px; }
/* a card closed by a new message keeps what was asked, not the controls */
.card.dismissed .chips, .card.dismissed .text-in, .card.dismissed [role=button], .card.dismissed .row input,
.card.dismissed .row .btn, .card.dismissed .field { display: none; }
.card-t { font-size: 13px; font-weight: 600; color: var(--agui-ink-2); margin-bottom: 10px; }
.card-q { font-size: 15px; font-weight: 600; margin-bottom: 10px; letter-spacing: -0.01em; }
.card .muted, .muted { color: var(--agui-ink-3); font-size: 13px; }
.acts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; align-items: center; }
.btn { white-space: nowrap; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 0; border-radius: var(--agui-button-radius, var(--agui-radius-pill));
  padding: 9px 15px; font: 600 13px/1 var(--agui-font); cursor: pointer; text-decoration: none; }
.btn.pri { background: var(--agui-button-bg, var(--agui-accent)); color: var(--agui-button-ink, var(--agui-on-accent)); }
.btn.sec { background: var(--agui-button-secondary-bg, var(--agui-bg)); color: var(--agui-button-secondary-ink, var(--agui-ink)); border: 1px solid var(--agui-button-secondary-border, var(--agui-line-2)); }
.btn.danger { background: var(--agui-danger); color: var(--agui-on-danger); }
.btn.link { background: none; padding: 4px 6px; color: var(--agui-link); font-weight: 550; }
.btn:disabled { opacity: .45; cursor: default; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { border: 1px solid var(--agui-chip-border, var(--agui-line-2)); background: var(--agui-chip-bg, var(--agui-bg)); color: var(--agui-chip-ink, var(--agui-ink-2));
  border-radius: var(--agui-chip-radius, var(--agui-radius-pill)); padding: 8px 13px;
  font: 13px/1.2 var(--agui-font); cursor: pointer; text-align: left; transition: border-color .2s, color .2s, background .2s; }
.chip:hover { border-color: var(--agui-ink-3); color: var(--agui-ink); }
.chip.on { background: var(--agui-chip-on-bg, var(--agui-accent)); border-color: var(--agui-chip-on-bg, var(--agui-accent)); color: var(--agui-chip-on-ink, var(--agui-on-accent)); }
.chip kbd { font: 11px/1 var(--agui-font); color: var(--agui-ink-3); margin-right: 6px; display: none; }
/* number-key hints only once the user works from the keyboard (the card or an option has keyboard focus) */
.card:focus-visible kbd, .card:has(:focus-visible) kbd { display: inline; }
.chip.on kbd { color: inherit; opacity: .7; }
.quick { margin: -8px 0 18px; animation: rise .4s var(--agui-ease) both; }
/* inputs, Apple-style: a soft filled field, 44 px tall, the accent ring on focus; 16 px text so iOS does not zoom */
.field input, .field select, .text-in { width: 100%; min-height: var(--agui-input-height, 44px); border: 1px solid var(--agui-input-border, transparent);
  border-radius: var(--agui-input-radius, var(--agui-radius-sm)); padding: 10px 14px; font: 16px/1.3 var(--agui-font);
  background: var(--agui-input-bg, var(--agui-soft)); color: var(--agui-input-ink, var(--agui-ink));
  transition: background .15s, border-color .15s, box-shadow .15s; }
.field input::placeholder, .text-in::placeholder { color: var(--agui-ink-3); }
.field input:focus, .field select:focus, .text-in:focus, .field input:focus-visible, .field select:focus-visible, .text-in:focus-visible {
  background: var(--agui-bg); border-color: var(--agui-link); box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 22%, transparent); }
input[type=number] { -moz-appearance: textfield; appearance: textfield; }
input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
:host(.dark) { color-scheme: dark; }   /* native date and time pickers follow the theme */
/* the number stepper: two halves on the right edge, full height, joined to the field's border */
.num { position: relative; display: block; }
.num > input { padding-right: 52px; }
/* the field's top margin moves to the wrapper, so the stepper stays aligned with the field */
.num > .text-in { margin-top: 0; }
.num:has(> .text-in) { margin-top: 10px; }
.fields .num, .field > .num { margin-top: 0; }
.num-step { position: absolute; top: 1px; right: 1px; bottom: 1px; width: 38px; display: grid; grid-template-rows: 1fr 1fr;
  border-left: 1px solid var(--agui-line-2); border-radius: 0 calc(var(--agui-radius-sm) - 1px) calc(var(--agui-radius-sm) - 1px) 0; overflow: hidden; }
.num-b { display: grid; place-items: center; border: 0; padding: 0; margin: 0; background: transparent; color: var(--agui-ink-2); cursor: pointer;
  transition: background .15s, color .15s; }
.num-b + .num-b { border-top: 1px solid var(--agui-line-2); }
.num-b:hover { background: color-mix(in srgb, var(--agui-ink) 6%, transparent); color: var(--agui-ink); }
.num-b:active { background: color-mix(in srgb, var(--agui-ink) 12%, transparent); }
.num-b svg { width: 12px; height: 12px; }
.num:has(> input[hidden]) { display: none; }
.field > .num, .field > .sel { flex: 1; min-width: 0; }
/* our calendar (calendar.ts): a month grid, round days, the accent for the chosen one, a ring for today */
.cal { margin-top: 10px; border: 1px solid var(--agui-line); border-radius: var(--agui-radius); padding: 10px; background: var(--agui-bg); max-width: 340px; }
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
.cal-wd { font-size: 11px; font-weight: 600; color: var(--agui-ink-3); padding: 4px 0; }
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
.date-face { display: flex; align-items: center; justify-content: space-between; gap: 8px; text-align: left; cursor: pointer; }
.date-face .ph { color: var(--agui-ink-3); }
.date-face .ico { color: var(--agui-ink-2); flex: none; }
.times { max-height: 196px; overflow: auto; }
input[type=date]::-webkit-calendar-picker-indicator, input[type=time]::-webkit-calendar-picker-indicator { display: none; }
/* checkboxes, Apple-style: a soft rounded square, the accent with a white tick when on */
.card input[type=checkbox] { appearance: none; -webkit-appearance: none; width: 20px; height: 20px; flex: none; margin: 2px 0 0; border-radius: 6px;
  border: 1.5px solid var(--agui-ink-3); background: var(--agui-bg); display: grid; place-items: center; cursor: pointer; transition: background .15s, border-color .15s; }
.card input[type=checkbox]::after { content: ''; width: 5px; height: 10px; border: solid var(--agui-on-accent); border-width: 0 2px 2px 0;
  transform: translateY(-1px) rotate(45deg) scale(0); transition: transform .15s; }
.card input[type=checkbox]:checked { background: var(--agui-accent); border-color: var(--agui-accent); }
.card input[type=checkbox]:checked::after { transform: translateY(-1px) rotate(45deg) scale(1); }
/* the slider, Apple-style: a thin soft track, the filled part in the accent, a white round thumb */
.range input[type=range] { appearance: none; -webkit-appearance: none; height: 28px; background: transparent; }
.range input[type=range]::-webkit-slider-runnable-track { height: 4px; border-radius: var(--agui-radius-pill);
  background: linear-gradient(to right, var(--agui-accent) var(--p, 50%), var(--agui-line-2) var(--p, 50%)); }
.range input[type=range]::-moz-range-track { height: 4px; border-radius: var(--agui-radius-pill); background: var(--agui-line-2); }
.range input[type=range]::-moz-range-progress { height: 4px; border-radius: var(--agui-radius-pill); background: var(--agui-accent); }
.range input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 26px; height: 26px; margin-top: -11px; border-radius: 50%;
  background: var(--agui-knob); border: 0.5px solid color-mix(in srgb, var(--agui-shadow) 40%, transparent); box-shadow: 0 2px 6px color-mix(in srgb, var(--agui-shadow) 60%, transparent); cursor: grab; }
.range input[type=range]::-moz-range-thumb { width: 26px; height: 26px; border-radius: 50%; background: var(--agui-knob); border: 0.5px solid color-mix(in srgb, var(--agui-shadow) 40%, transparent);
  box-shadow: 0 2px 6px color-mix(in srgb, var(--agui-shadow) 60%, transparent); cursor: grab; }
/* selects: the native arrow hidden, a chevron of our own */
.sel { position: relative; display: block; }
.sel select { appearance: none; -webkit-appearance: none; padding-right: 40px; cursor: pointer; }
.sel::after { content: ''; position: absolute; right: 16px; top: 50%; width: 7px; height: 7px; border-right: 1.8px solid var(--agui-ink-2);
  border-bottom: 1.8px solid var(--agui-ink-2); transform: translateY(-70%) rotate(45deg); pointer-events: none; }
.text-in { margin-top: 10px; }
.raw { font: 12px/1.4 ui-monospace, Menlo, monospace; white-space: pre-wrap; max-height: 160px; overflow: auto; color: var(--agui-ink-2); }
.ok-line { display: flex; gap: 9px; align-items: center; font-size: 13px; color: var(--agui-ink-2); }
.ok-line i { width: 20px; height: 20px; border-radius: var(--agui-radius-pill); background: var(--agui-ok); color: var(--agui-on-ok); display: grid; place-items: center; font-style: normal;
  font-size: 11px; font-weight: 700; flex: none; }
.ok-line.off i { background: var(--agui-ink-3); }
.tool-el { margin: 0 0 18px; }
.fcard.folded:not(.unfolded) .row, .fcard.folded:not(.unfolded) .card-t { display: none; }
.fcard.folded .ok-line { margin-top: 0; }
.fcard.folded.unfolded .ok-line { margin-top: 8px; }
.fold { display: flex; gap: 9px; align-items: center; min-width: 0; flex: 1; border: 0; background: none; padding: 0; color: inherit;
  font: inherit; text-align: left; cursor: pointer; }
.fold { border-radius: var(--agui-radius-sm); }
.fold span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fold .chev { flex: none; color: var(--agui-ink-3); transition: transform .2s; }
.fcard.unfolded .fold .chev { transform: rotate(90deg); }
.after { font-weight: 400; }
.chip.act { border-color: var(--agui-ok); color: var(--agui-ink); }
.chip.act i { font-style: normal; color: var(--agui-ok); font-weight: 700; margin-right: 6px; }
.applied { margin: 0 0 16px; }
.row { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-top: 1px solid var(--agui-line); transition: opacity .2s; }
.row.off { opacity: .5; }
.row input[type=checkbox] { margin-top: 4px; }
.row-main { flex: 1; min-width: 0; }
.row-label { font-size: 12px; }
.row-tools { display: flex; gap: 2px; flex: none; }
.was { display: block; font-size: 13px; margin-bottom: 1px; }   /* old above new, like a tracked change */
.field { flex: 1; display: flex; gap: 6px; align-items: center; }
.zone { border: 1.5px dashed var(--agui-line-2); border-radius: var(--agui-radius); padding: 16px; text-align: center; cursor: pointer; transition: border-color .2s; }
.zone.over { border-color: var(--agui-link); }
.zone .muted { margin-top: 4px; }
.link-text { color: var(--agui-link); }
.bar { height: 4px; border-radius: var(--agui-radius-pill); background: var(--agui-line); overflow: hidden; margin-top: 12px; }
.bar > div { height: 100%; width: 0; background: var(--agui-link); transition: width .2s; }
.card-msg { color: var(--agui-ink-2); }
.err-line { color: var(--agui-danger); margin-top: 8px; }
.err-line:empty { display: none; }
.wait .slow { margin-left: 10px; font-size: 13px; color: var(--agui-ink-3); animation: rise .4s var(--agui-ease) both; }

/* composer */
.foot { padding: 10px 14px max(14px, env(safe-area-inset-bottom, 0px)); background: var(--agui-composer-area-bg, transparent); }
.box { display: flex; align-items: flex-end; gap: 8px; background: var(--agui-composer-bg, var(--agui-bg)); border: 1px solid var(--agui-composer-border, var(--agui-line-2));
  border-radius: var(--agui-composer-radius, var(--agui-radius-lg));
  padding: 8px 8px 8px 18px; box-shadow: 0 1px 2px color-mix(in srgb, var(--agui-shadow) 15%, transparent); transition: border-color .2s, box-shadow .2s; }
.box:focus-within { border-color: var(--agui-ink-3); }
.box.drop { border-color: var(--agui-accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-accent) 25%, transparent); }   /* a file dragged over it */
.box textarea { flex: 1; border: 0; outline: none; resize: none; background: transparent; color: var(--agui-ink); font: 16px/1.4 var(--agui-font);
  padding: 7px 0; max-height: 180px; min-height: 24px; }
.box textarea:placeholder-shown { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.send { width: 36px; height: 36px; border: 0; border-radius: var(--agui-radius-pill); background: var(--agui-accent); color: var(--agui-on-accent); cursor: pointer;
  display: grid; place-items: center; flex: none; transition: opacity .2s, transform .15s; }
.send.idle { opacity: .3; cursor: default; }   /* not "empty": that is the empty chat's class */
.send svg, .ib svg { width: 17px; height: 17px; }
.ib { width: 36px; height: 36px; border: 0; border-radius: var(--agui-radius-pill); background: transparent; color: var(--agui-ink-2); cursor: pointer; display: grid;
  place-items: center; flex: none; transition: background .2s, color .2s; }
.ib:hover { background: var(--agui-soft); }
.mic.on { background: var(--agui-danger); color: var(--agui-on-danger); animation: rec 1.4s ease-out infinite; }
@keyframes rec { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--agui-danger) 45%, transparent); } 100% { box-shadow: 0 0 0 12px transparent; } }
.nudge .box { animation: nudge .4s; }
@keyframes nudge { 25% { transform: translateX(-6px); } 50% { transform: translateX(5px); } 75% { transform: translateX(-3px); } }
.files { margin: 0 0 8px; } .files[hidden] { display: none; }
.chip.file { display: inline-flex; align-items: center; gap: 4px; padding: 4px 4px 4px 11px; cursor: default; }
.chip.file .btn { padding: 2px 7px; }
.hint { text-align: center; font-size: 12px; color: var(--agui-ink-3); margin-top: 7px; min-height: 1em; }
.hint .btn.link { font-size: 12px; padding: 0 2px; }
/* dictation on the server: the wave and the timer take the input's place, like iOS Messages' dictation */
.rec-x, .wave, .rec-busy { display: none; }
.box.rec { align-items: center; padding-left: 8px; }
.box.rec .rec-x { display: grid; }
.box.rec .clip, .box.rec textarea { display: none; }
.box.rec .wave { display: flex; flex: 1; min-width: 0; align-items: center; gap: 10px; height: 36px; }
.wave .bars { flex: 1; min-width: 0; display: flex; align-items: center; justify-content: flex-end; gap: 2px; height: 28px; overflow: hidden; }
.wave .bars i { flex: none; width: 3px; height: 3px; border-radius: var(--agui-radius-pill); background: var(--agui-ink-3); transition: height 80ms linear; }
.wave .rec-time { flex: none; font: 13px/1 var(--agui-font); font-variant-numeric: tabular-nums; color: var(--agui-ink-2); min-width: 2.6em; text-align: right; }
.box.busy .bars, .box.busy .rec-time { display: none; }
.box.busy .rec-busy { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--agui-ink-2); }
.box.busy .rec-busy .dots { padding: 0; }
/* one control at a time, like iOS: while recording only the red mic stops it (no dimmed send next to it);
   while transcribing there is nothing to tap but the cancel on the left */
.box.rec .send { display: none; }
.box.busy .mic { display: none; }
@media (prefers-reduced-motion: reduce) { .wave .bars i { transition: none; } }

/* phones: fingers need 44 px */
@media (pointer: coarse) {
  .icon, .ib, .send { width: 44px; height: 44px; }
  .chip { min-height: 44px; padding: 10px 14px; }
  .btn { min-height: 44px; }
  .btn.link { min-height: 44px; padding: 4px 10px; }
  .chip.file .btn { min-height: 32px; }
}
@media (max-width: 760px) {
  .mode-floating .panel { width: 100vw; box-shadow: none; transform: translateY(100%); }
  .mode-floating.open .panel { transform: none; }
}
/* bubble mode: a round launcher that grows into a chat window (iMessage / Intercom-like), Apple-style spring */
.mode-bubble .scrim { display: none; }
.mode-bubble .fab { width: var(--agui-launcher-size, 60px); height: var(--agui-launcher-size, 60px); padding: 0; justify-content: center; gap: 0;
  border-radius: var(--agui-radius-pill); bottom: max(var(--agui-bubble-offset, 20px), env(safe-area-inset-bottom, 0px));
  transition: transform .35s var(--agui-ease), opacity .35s var(--agui-ease), box-shadow .2s; }
.mode-bubble.side-left .fab { right: auto; left: max(var(--agui-bubble-offset, 20px), env(safe-area-inset-left, 0px)); }
.mode-bubble .fab-label { display: none; }
.mode-bubble .fab:hover { box-shadow: 0 14px 36px -8px var(--agui-shadow); }
.mode-bubble .fab:active { transform: scale(.94); }
.fab-ico, .fab-x, .fab-own { display: grid; place-items: center; }
.fab-x, .fab-own:empty, .fab-dot { display: none; }
.mode-bubble .fab-ico, .mode-bubble .fab-x { position: absolute; inset: 0; transition: transform .35s cubic-bezier(.34, 1.4, .5, 1), opacity .2s; }
.mode-bubble .fab-ico svg, .mode-bubble .fab-x svg { width: 26px; height: 26px; }
.mode-bubble .fab-x { display: grid; opacity: 0; transform: rotate(-90deg) scale(.6); }
.mode-bubble.open .fab, .mode-bubble.closing .fab { opacity: 1; pointer-events: auto; }
.mode-bubble.open .fab-ico { opacity: 0; transform: rotate(90deg) scale(.6); }
.mode-bubble.open .fab-x { opacity: 1; transform: none; }
.mode-bubble .fab.own .fab-ico, .mode-bubble .fab.own:not(.x) .fab-x { display: none; }
.mode-bubble .fab-own { position: absolute; inset: 0; border-radius: inherit; overflow: hidden; }
.mode-bubble.open .fab.own .fab-own { opacity: 0; } .mode-bubble.open .fab.own .fab-x { display: grid; }
.mode-bubble .fab-dot { display: block; position: absolute; top: 3px; right: 3px; width: 14px; height: 14px; border-radius: var(--agui-radius-pill);
  background: var(--agui-danger); border: 2px solid var(--agui-bg); transform: scale(0); transition: transform .3s cubic-bezier(.34, 1.6, .5, 1); }
.mode-bubble .fab.unread .fab-dot { transform: scale(1); }
.mode-bubble .fab.bounce { animation: agui-bounce .6s cubic-bezier(.34, 1.6, .5, 1); }
@keyframes agui-bounce { 0% { transform: scale(1); } 30% { transform: scale(1.12) translateY(-4px); } 60% { transform: scale(.96); } 100% { transform: scale(1); } }
/* the window: grows out of the launcher's corner */
.mode-bubble .panel { position: fixed; z-index: 2147483001; right: max(var(--agui-bubble-offset, 20px), env(safe-area-inset-right, 0px));
  bottom: calc(max(var(--agui-bubble-offset, 20px), env(safe-area-inset-bottom, 0px)) + var(--agui-launcher-size, 60px) + 14px);
  width: min(var(--agui-bubble-width, 400px), calc(100vw - 32px)); height: min(var(--agui-bubble-height, 680px), calc(100vh - 120px));
  border-radius: var(--agui-bubble-window-radius, 24px); overflow: hidden; border: 1px solid var(--agui-line);
  box-shadow: 0 24px 60px -16px var(--agui-shadow), 0 4px 14px -6px color-mix(in srgb, var(--agui-shadow) 50%, transparent);
  transform-origin: bottom right; visibility: hidden; opacity: 0; transform: translateY(16px) scale(.18); }
.mode-bubble.side-left .panel { right: auto; left: max(var(--agui-bubble-offset, 20px), env(safe-area-inset-left, 0px)); transform-origin: bottom left; }
.mode-bubble.open .panel { visibility: visible; opacity: 1; transform: none; animation: agui-grow .52s cubic-bezier(.34, 1.4, .5, 1) both; }   /* static end state for reduced motion */
.mode-bubble.closing .panel { visibility: visible; animation: agui-shrink .22s cubic-bezier(.4, 0, 1, 1) both; }
@keyframes agui-grow {
  0% { opacity: 0; transform: translateY(16px) scale(.18); border-radius: 40px; }
  35% { opacity: 1; }
  100% { opacity: 1; transform: none; border-radius: var(--agui-bubble-window-radius, 24px); } }
@keyframes agui-shrink {
  0% { opacity: 1; transform: none; }
  100% { opacity: 0; transform: translateY(16px) scale(.18); border-radius: 40px; } }
/* the content rises in, one after another */
.mode-bubble.open .head, .mode-bubble.open .log, .mode-bubble.open .foot { animation: agui-rise .42s cubic-bezier(.2, .8, .2, 1) both; }
.mode-bubble.open .head { animation-delay: .12s; } .mode-bubble.open .log { animation-delay: .18s; } .mode-bubble.open .foot { animation-delay: .24s; }
@keyframes agui-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.mode-bubble .close { display: none; }   /* the launcher closes it */
/* motion options */
.motion-gentle.mode-bubble.open .panel { animation-duration: .32s; animation-timing-function: cubic-bezier(.2, .8, .2, 1); }
.motion-none.mode-bubble.open .panel, .motion-none.mode-bubble.closing .panel { animation: agui-fade .2s ease both; transform: none; }
.motion-none.mode-bubble.closing .panel { animation-direction: reverse; }
.motion-none.mode-bubble.open .head, .motion-none.mode-bubble.open .log, .motion-none.mode-bubble.open .foot { animation: none; }
@keyframes agui-fade { from { opacity: 0; } to { opacity: 1; } }
/* the greeting: a small speech bubble next to the closed launcher */
.greet { position: fixed; z-index: 2147483000; right: calc(max(var(--agui-bubble-offset, 20px), env(safe-area-inset-right, 0px)) + var(--agui-launcher-size, 60px) + 12px);
  bottom: calc(max(var(--agui-bubble-offset, 20px), env(safe-area-inset-bottom, 0px)) + 8px); display: flex; align-items: flex-start; gap: 4px;
  max-width: min(280px, calc(100vw - 120px)); background: var(--agui-bg); color: var(--agui-ink); border: 1px solid var(--agui-line);
  border-radius: 18px 18px 4px 18px; padding: 10px 8px 10px 14px; box-shadow: 0 12px 32px -12px var(--agui-shadow);
  opacity: 0; transform: translateY(8px) scale(.9); transform-origin: bottom right; transition: opacity .3s, transform .4s cubic-bezier(.34, 1.4, .5, 1); }
.side-left .greet { right: auto; left: calc(max(var(--agui-bubble-offset, 20px), env(safe-area-inset-left, 0px)) + var(--agui-launcher-size, 60px) + 12px);
  border-radius: 18px 18px 18px 4px; transform-origin: bottom left; }
.greet.show { opacity: 1; transform: none; }
.greet-body { border: 0; background: none; color: inherit; font: 15px/1.35 var(--agui-font); text-align: left; padding: 0; cursor: pointer; }
.greet-x { border: 0; background: none; color: var(--agui-ink-3); font-size: 17px; line-height: 1; width: 24px; height: 24px; border-radius: var(--agui-radius-pill); cursor: pointer; flex: none; }
.greet-x:hover { background: var(--agui-soft); color: var(--agui-ink); }
.mode-bubble.open .greet, :not(.mode-bubble) > .greet { display: none; }
/* phones: the window is a sheet from the bottom with a grabber; the page is dimmed */
@media (max-width: 520px) {
  .mode-bubble .scrim { display: block; }
  .mode-bubble.open .scrim { opacity: 1; pointer-events: auto; }
  .mode-bubble .panel { left: 0; right: 0; bottom: 0; width: 100vw; height: min(92vh, 100%); border-radius: 22px 22px 0 0; border-width: 1px 0 0;
    transform-origin: bottom center; transform: translateY(100%); }
  .mode-bubble.open .panel { animation: agui-sheet .42s cubic-bezier(.2, .9, .25, 1.05) both; }
  .mode-bubble.closing .panel { animation: agui-sheet-out .24s cubic-bezier(.4, 0, 1, 1) both; }
  .mode-bubble .panel::before { content: ''; position: absolute; top: 6px; left: 50%; width: 36px; height: 5px; margin-left: -18px; border-radius: 3px; background: var(--agui-line-2); }
  .mode-bubble .close { display: grid; }
  .mode-bubble.open .fab { opacity: 0; pointer-events: none; }
  .greet { max-width: calc(100vw - 110px); }
}
@keyframes agui-sheet { from { transform: translateY(100%); } to { transform: none; } }
@keyframes agui-sheet-out { from { transform: none; } to { transform: translateY(100%); } }
/* card kit: richer looks of the same cards (pickers.ts); tokens and scales only */
.opts { display: grid; gap: 6px; }
.opt { display: grid; gap: 2px; text-align: left; border: 1px solid var(--agui-option-border, var(--agui-line-2)); background: var(--agui-option-bg, var(--agui-bg));
  color: var(--agui-option-ink, var(--agui-ink)); border-radius: var(--agui-option-radius, var(--agui-radius-sm)); padding: 10px 12px; cursor: pointer; font: inherit; position: relative; transition: border-color .2s; }
.opt:hover { border-color: var(--agui-ink-3); }
.opt b { font-weight: 600; }
.opt .muted { font-size: 13px; }
.opt kbd { position: absolute; right: 10px; top: 10px; font: 11px/1 var(--agui-font); color: var(--agui-ink-3); display: none; }
.opt.on { border-color: var(--agui-accent); box-shadow: inset 0 0 0 1px var(--agui-accent); }
.cmp { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 6px; }
.cmp-col { align-content: start; }
.cmp-col.rec { border-color: var(--agui-accent); box-shadow: inset 0 0 0 1px var(--agui-accent); }
.cmp-v { display: grid; gap: 0; font-size: 13px; margin-top: 4px; }
.cmp-v > span:last-child { white-space: nowrap; font-weight: 600; font-size: 15px; }
.cmp-v .muted { font-size: 12px; }
.tag { display: inline-block; font-size: 11px; font-weight: 600; border-radius: var(--agui-radius-pill); padding: 2px 8px;
  background: var(--agui-soft); color: var(--agui-ink-2); margin-left: 6px; vertical-align: 1px; }
.cmp-col .tag { margin: 0 0 4px; justify-self: start; }
.tag.warn { background: color-mix(in srgb, var(--agui-danger) 12%, transparent); color: var(--agui-danger); }
.note { margin-top: 6px; font-size: 12px; }
.search { margin: 0 0 8px; }
.strip .btn.link { margin-top: 6px; }
.slots { margin-top: 8px; }
.range input[type=range] { width: 100%; margin: 4px 0; }
.range-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.range-v { font-weight: 600; }
.range-p { font-size: 17px; font-weight: 600; }
.stepper { display: inline-flex; align-items: center; gap: 4px; }
.stepper .btn { width: 36px; height: 36px; min-height: 36px; padding: 0; display: grid; place-items: center; font-size: 17px; line-height: 1;
  border-radius: var(--agui-radius-pill); }
.stepper .range-v { min-width: 44px; padding: 0 4px; text-align: center; font-size: 17px; font-variant-numeric: tabular-nums; }
.fields { display: grid; gap: 8px; }
.fields .text-in { margin-top: 0; }
.fld { display: grid; gap: 4px; }
.fld .muted { font-size: 12px; }
.row.consent { cursor: pointer; }
.issue-line { font-size: 13px; margin-top: 2px; display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
.issue-line.warning { color: color-mix(in srgb, var(--agui-danger) 70%, var(--agui-ink)); }
.issue-line.error, .row.issue.error .sev { color: var(--agui-danger); }
.why, .doc, .quote { margin-top: 4px; font-size: 13px; }
.shared { margin: -4px 0 8px; font-size: 13px; }
.doc-head { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.doc-head .thumb { width: 44px; height: 32px; border-radius: var(--agui-radius-sm); background: var(--agui-soft); object-fit: cover; flex: none; }
.rev .row { width: 100%; border-left: 0; border-right: 0; border-bottom: 0; background: none; color: inherit; font: inherit; text-align: left; }
.rev-s { cursor: pointer; align-items: center; }
.rev-s .dot { width: 14px; height: 14px; border: 1.5px dashed var(--agui-ink-3); border-radius: var(--agui-radius-pill); flex: none; }
.rev-s .okmark { width: 14px; color: var(--agui-ok); font-style: normal; font-weight: 700; flex: none; }
.row.issue .sev { width: 14px; font-style: normal; font-weight: 700; flex: none; color: var(--agui-ink-3); }
.row.issue.fixed .sev { color: var(--agui-ok); }
.row.issue .ok-line { margin-top: 4px; }
.srcs { margin: -10px 0 18px; }
.src-chip { font-size: 12px; padding: 5px 10px; }
.why .src-chip { display: inline-block; margin-left: 6px; border: 1px solid var(--agui-line-2); border-radius: var(--agui-radius-pill); }
.details { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 8px 0 0; font-size: 14px; }
.details dt, .details dd { margin: 0; }
.consequence { margin-top: 8px; }
.card[part~=card-confirm] > .ok-line { margin-top: 12px; }   /* the result replaces the action row: keep the gap */
.receipt { display: grid; gap: 6px; margin-top: 12px; }
.receipt-n { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; font-size: 14px; }
.feedback { display: flex; gap: 4px; align-items: center; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--agui-line); }
.feedback .thumb { font-size: 16px; padding: 2px 8px; }
.privacy { margin-top: 8px; }
@media (max-width: 520px) {
  .fcard .acts, .rev .acts { position: sticky; bottom: 0; background: var(--agui-card-bg, var(--agui-surface)); -webkit-backdrop-filter: var(--agui-card-blur, none); backdrop-filter: var(--agui-card-blur, none); padding: 8px 0 2px; margin-bottom: -2px; }
  .cmp { grid-template-columns: 1fr; }
}
@media (pointer: coarse) {
  .row input[type=checkbox] { width: 22px; height: 22px; }
  .row { min-height: 44px; }
  .opt { min-height: 44px; }
  .stepper .btn { width: 44px; height: 44px; }
  .num-step { width: 44px; }
  .num > input { padding-right: 58px; }
}
:host(.calm) *, :host(.calm) *::before, :host(.calm) *::after { animation: none !important; transition: none !important; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
`

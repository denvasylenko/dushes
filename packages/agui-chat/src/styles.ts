/**
 * The chat's styles, in its shadow root. The look and motion follow the Cheese project's chat
 * (Herefront AI, chat.css); every colour, radius and font is a token you can set on the element:
 *   agui-chat { --agui-accent: #0a7; --agui-radius: 6px; }
 * Parts for deeper changes: panel, header, log, message, user, assistant, steps, card, chip, composer,
 * input, send, fab (e.g. agui-chat::part(card) { border-width: 2px }).
 */
export const CSS = `
:host { --agui-accent: #1d1d1f; --agui-on-accent: #fff; --agui-link: #0071e3; --agui-bg: #fff; --agui-surface: #fafafb;
  --agui-soft: #f2f2f5; --agui-ink: #1d1d1f; --agui-ink-2: #6e6e73; --agui-ink-3: #86868b; --agui-line: #ececf0;
  --agui-line-2: #e3e3e8; --agui-ok: #34c759; --agui-danger: #ff3b30; --agui-radius: 14px; --agui-panel-width: 460px;
  --agui-font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Helvetica Neue", Arial, sans-serif;
  --agui-ease: cubic-bezier(.28, .11, .32, 1); --agui-fade: 450ms;
  display: block; font-family: var(--agui-font); color: var(--agui-ink); letter-spacing: -0.01em; }
:host([hidden]) { display: none; }
:host(.dark) { --agui-accent: #f5f5f7; --agui-on-accent: #1d1d1f; --agui-link: #4ea1ff; --agui-bg: #1c1c1e; --agui-surface: #242426;
  --agui-soft: #2c2c2e; --agui-ink: #f5f5f7; --agui-ink-2: #aeaeb2; --agui-ink-3: #8e8e93; --agui-line: #333336; --agui-line-2: #3a3a3c; }
* { box-sizing: border-box; }
[hidden] { display: none !important; }
button { font: inherit; color: inherit; }
button:focus, input:focus, [tabindex]:focus { outline: none; }
/* a soft ring for the keyboard only */
button:focus-visible, input:focus-visible, select:focus-visible, [tabindex]:focus-visible { outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 35%, transparent); }
.card:focus-visible { box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-link) 22%, transparent); }

/* layout: floating (button + side panel), inline (fills its box), page (the whole window) */
.panel { display: flex; flex-direction: column; background: var(--agui-bg); color: var(--agui-ink); min-height: 0; text-align: left; }
.mode-inline { height: 100%; }
.mode-inline .panel { height: 100%; border: 1px solid var(--agui-line); border-radius: var(--agui-radius); overflow: hidden; }
.mode-page .panel { position: fixed; inset: 0; }
.mode-page .log, .mode-page .foot { width: min(760px, 100%); margin: 0 auto; }
.mode-floating .panel { position: fixed; z-index: 2147483001; top: 0; right: 0; bottom: 0; width: min(var(--agui-panel-width), 100vw);
  box-shadow: -20px 0 60px -20px rgba(0,0,0,.3); transform: translateX(104%); transition: transform .42s var(--agui-ease); visibility: hidden; }
.mode-floating.open .panel { transform: none; visibility: visible; }
.scrim { position: fixed; inset: 0; z-index: 2147483000; background: rgba(0,0,0,.18); opacity: 0; pointer-events: none; transition: opacity .3s; }
.mode-floating.open .scrim { opacity: 1; pointer-events: auto; }
.mode-inline .scrim, .mode-page .scrim, .mode-inline .fab, .mode-page .fab { display: none; }
.fab { position: fixed; z-index: 2147482999; right: max(20px, env(safe-area-inset-right, 0px)); bottom: max(20px, env(safe-area-inset-bottom, 0px));
  display: flex; align-items: center; gap: 9px; border: 0; border-radius: 999px; padding: 13px 20px 13px 16px; cursor: pointer;
  background: var(--agui-accent); color: var(--agui-on-accent); font: 600 15px/1 var(--agui-font); box-shadow: 0 10px 30px -8px rgba(0,0,0,.45);
  transform: translateY(20px); opacity: 0; transition: transform .35s var(--agui-ease), opacity .35s var(--agui-ease); }
.fab.show { transform: none; opacity: 1; }
.mode-floating.open .fab { opacity: 0; pointer-events: none; }
.fab svg, .spark { width: 18px; height: 18px; flex: none; }

/* header */
.head { display: flex; align-items: center; gap: 12px; padding: 14px 14px 12px 20px; border-bottom: 1px solid var(--agui-line); }
.logo { width: 32px; height: 32px; border-radius: 10px; flex: none; display: grid; place-items: center; background: var(--agui-accent); color: var(--agui-on-accent); }
.title { font-weight: 650; font-size: 15px; line-height: 1.2; }
.sub { font-size: 12px; color: var(--agui-ink-3); margin-top: 2px; }
.icon { flex: none; width: 36px; height: 36px; border: 0; border-radius: 10px; background: transparent; color: var(--agui-ink-2);
  display: grid; place-items: center; cursor: pointer; }
.head .icon:first-of-type { margin-left: auto; }
.icon:hover { background: var(--agui-soft); color: var(--agui-ink); }
.icon svg { width: 19px; height: 19px; }
.mode-inline .close, .mode-page .close { display: none; }

/* messages */
.log { flex: 1; overflow-y: auto; padding: 22px 20px 12px; overscroll-behavior: contain; min-height: 0; }
.empty { padding: 22px 2px 10px; }
.empty h3 { font-size: 28px; line-height: 1.15; letter-spacing: -0.035em; margin: 0 0 8px; text-wrap: balance; }
.empty p { margin: 0 0 18px; color: var(--agui-ink-2); font-size: 15px; line-height: 1.45; }
.msg { margin: 0 0 20px; font-size: 15px; line-height: 1.58; letter-spacing: -0.008em; overflow-wrap: anywhere; }
.msg.me { display: flex; justify-content: flex-end; }
.msg.me > div { background: var(--agui-soft); border-radius: 20px; padding: 10px 15px; max-width: 85%; white-space: pre-wrap; }
.msg.ai p { margin: 0 0 10px; } .msg.ai p:last-child { margin-bottom: 0; }
.msg.ai ul { margin: 4px 0 10px; padding-left: 20px; } .msg.ai li { margin: 3px 0; }
.msg.ai a { color: var(--agui-link); }
.msg.ai code { font-size: .9em; background: var(--agui-soft); border-radius: 6px; padding: 1px 5px; }
.notice { text-align: center; font-size: 12px; color: var(--agui-ink-3); margin: 0 0 16px; }
.error { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; color: var(--agui-danger); font-size: 13px; margin: 0 0 16px; }
.dots { display: inline-flex; gap: 4px; padding: 8px 0; }
.dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--agui-ink-3); opacity: .5; animation: bounce 1.2s infinite; }
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
.steps li .mark { width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--agui-line-2); flex: none; display: grid; place-items: center; }
.steps li.run .mark { border-color: var(--agui-line-2); border-top-color: var(--agui-link); animation: turn .8s linear infinite; }
.steps li.ok { color: var(--agui-ink-2); }
.steps li.ok .mark { border-color: var(--agui-ok); background: var(--agui-ok) center/10px no-repeat
  url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'%3E%3Cpath d='M2.5 6.2 5 8.6l4.5-5' fill='none' stroke='%23fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  animation: tick .3s both; }
.steps li.fail .mark { border-color: var(--agui-danger); background: var(--agui-danger); }
.steps li.sub .mark { width: 12px; height: 12px; border-width: 1.5px; background-size: 8px; }
@keyframes turn { to { transform: rotate(360deg); } }
@keyframes tick { from { transform: scale(.6); } to { transform: none; } }

/* cards inside the conversation */
.card { margin: 4px 0 20px; border: 1px solid var(--agui-line); border-radius: var(--agui-radius); background: var(--agui-surface); padding: 14px;
  animation: rise .5s var(--agui-ease) both; font-size: 15px; line-height: 1.45; }
@keyframes rise { from { opacity: 0; transform: translateY(8px) scale(.98); } to { opacity: 1; transform: none; } }
.card.done { opacity: .72; }
.card input[type=checkbox], .chip input[type=checkbox] { accent-color: var(--agui-accent); width: 15px; height: 15px; }
/* a card closed by a new message keeps what was asked, not the controls */
.card.dismissed .chips, .card.dismissed .text-in, .card.dismissed [role=button], .card.dismissed .row input,
.card.dismissed .row .btn, .card.dismissed .field { display: none; }
.card-t { font-size: 13px; font-weight: 600; color: var(--agui-ink-2); margin-bottom: 10px; }
.card-q { font-size: 15px; font-weight: 600; margin-bottom: 10px; letter-spacing: -0.01em; }
.card .muted, .muted { color: var(--agui-ink-3); font-size: 13px; }
.acts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; align-items: center; }
.btn { white-space: nowrap; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 0; border-radius: 999px;
  padding: 9px 15px; font: 600 13px/1 var(--agui-font); cursor: pointer; text-decoration: none; }
.btn.pri { background: var(--agui-accent); color: var(--agui-on-accent); }
.btn.sec { background: var(--agui-bg); color: var(--agui-ink); border: 1px solid var(--agui-line-2); }
.btn.danger { background: var(--agui-danger); color: #fff; }
.btn.link { background: none; padding: 4px 6px; color: var(--agui-link); font-weight: 550; }
.btn:disabled { opacity: .45; cursor: default; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { border: 1px solid var(--agui-line-2); background: var(--agui-bg); color: var(--agui-ink-2); border-radius: 999px; padding: 8px 13px;
  font: 13px/1.2 var(--agui-font); cursor: pointer; text-align: left; transition: border-color .2s, color .2s, background .2s; }
.chip:hover { border-color: var(--agui-ink-3); color: var(--agui-ink); }
.chip.on { background: var(--agui-accent); border-color: var(--agui-accent); color: var(--agui-on-accent); }
.chip kbd { font: 11px/1 var(--agui-font); color: var(--agui-ink-3); margin-right: 6px; }
.chip.on kbd { color: inherit; opacity: .7; }
.quick { margin: -8px 0 18px; animation: rise .4s var(--agui-ease) both; }
.field input, .field select, .text-in { width: 100%; border: 1px solid var(--agui-line-2); border-radius: 10px; padding: 9px 12px;
  font: 15px/1.3 var(--agui-font); background: var(--agui-bg); color: var(--agui-ink); }
.text-in { margin-top: 10px; }
.raw { font: 12px/1.4 ui-monospace, Menlo, monospace; white-space: pre-wrap; max-height: 160px; overflow: auto; color: var(--agui-ink-2); }
.ok-line { display: flex; gap: 9px; align-items: center; font-size: 13px; color: var(--agui-ink-2); }
.ok-line i { width: 20px; height: 20px; border-radius: 50%; background: var(--agui-ok); color: #fff; display: grid; place-items: center; font-style: normal;
  font-size: 11px; font-weight: 700; flex: none; }
.ok-line.off i { background: var(--agui-ink-3); }
.tool-el { margin: 0 0 18px; }
.row { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-top: 1px solid var(--agui-line); transition: opacity .2s; }
.row.off { opacity: .5; }
.row input[type=checkbox] { margin-top: 4px; }
.row-main { flex: 1; min-width: 0; }
.row-label { font-size: 12px; }
.row-tools { display: flex; gap: 2px; flex: none; }
.was { margin-right: 6px; }
.field { flex: 1; display: flex; gap: 6px; align-items: center; }
.zone { border: 1.5px dashed var(--agui-line-2); border-radius: 14px; padding: 16px; text-align: center; cursor: pointer; transition: border-color .2s; }
.zone.over { border-color: var(--agui-link); }
.zone .muted { margin-top: 4px; }
.link-text { color: var(--agui-link); }
.bar { height: 4px; border-radius: 999px; background: var(--agui-line); overflow: hidden; margin-top: 12px; }
.bar > div { height: 100%; width: 0; background: var(--agui-link); transition: width .2s; }
.card-msg { color: var(--agui-ink-2); }
.err-line { color: var(--agui-danger); margin-top: 8px; }
.err-line:empty { display: none; }
.wait .slow { margin-left: 10px; font-size: 13px; color: var(--agui-ink-3); animation: rise .4s var(--agui-ease) both; }

/* composer */
.foot { padding: 10px 14px max(14px, env(safe-area-inset-bottom, 0px)); }
.box { display: flex; align-items: flex-end; gap: 8px; background: var(--agui-bg); border: 1px solid var(--agui-line-2); border-radius: 20px;
  padding: 8px 8px 8px 18px; box-shadow: 0 1px 2px rgba(0,0,0,.04); transition: border-color .2s, box-shadow .2s; }
.box:focus-within { border-color: var(--agui-ink-3); }
.box textarea { flex: 1; border: 0; outline: none; resize: none; background: transparent; color: var(--agui-ink); font: 16px/1.4 var(--agui-font);
  padding: 7px 0; max-height: 180px; min-height: 24px; }
.box textarea:placeholder-shown { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.send { width: 36px; height: 36px; border: 0; border-radius: 50%; background: var(--agui-accent); color: var(--agui-on-accent); cursor: pointer;
  display: grid; place-items: center; flex: none; transition: opacity .2s, transform .15s; }
.send.empty { opacity: .3; cursor: default; }
.send svg, .ib svg { width: 17px; height: 17px; }
.ib { width: 36px; height: 36px; border: 0; border-radius: 50%; background: transparent; color: var(--agui-ink-2); cursor: pointer; display: grid;
  place-items: center; flex: none; transition: background .2s, color .2s; }
.ib:hover { background: var(--agui-soft); }
.mic.on { background: var(--agui-danger); color: #fff; animation: rec 1.4s ease-out infinite; }
@keyframes rec { 0% { box-shadow: 0 0 0 0 rgba(255, 59, 48, .45); } 100% { box-shadow: 0 0 0 12px rgba(255, 59, 48, 0); } }
.nudge .box { animation: nudge .4s; }
@keyframes nudge { 25% { transform: translateX(-6px); } 50% { transform: translateX(5px); } 75% { transform: translateX(-3px); } }
.files { margin: 0 0 8px; } .files[hidden] { display: none; }
.chip.file { display: inline-flex; align-items: center; gap: 4px; padding: 4px 4px 4px 11px; cursor: default; }
.chip.file .btn { padding: 2px 7px; }
.hint { text-align: center; font-size: 12px; color: var(--agui-ink-3); margin-top: 7px; min-height: 1em; }

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
:host(.calm) *, :host(.calm) *::before, :host(.calm) *::after { animation: none !important; transition: none !important; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
`

/** The voice mode's look, with the chat's tokens: the orb above the input (a flat sky of the voice colour and a white
 *  cloud that goes round), its one step line, the row (the composer, the microphone, the close button) and the code
 *  sheet. The orb keeps one box (`--agui-voice-orb`, 76) and changes by transform only, so the conversation never
 *  moves with its state: x .9 and lifted while thinking, x .66 at rest and silent (the shared ratios). */
export const VOICE_CSS = `:host { --agui-voice: var(--agui-voice-accent, var(--agui-link)); --agui-on-voice: #fff; --agui-voice-cloud: #fff; }
:host(.dark) { --agui-on-voice: #1d1d1f; }
.vo-dock { display: grid; justify-items: center; align-content: end; gap: 8px; box-sizing: border-box; height: calc(var(--agui-voice-orb, 76px) + 38px); padding: 4px 0 8px; overflow: hidden;
  animation: vo-in .2s var(--agui-ease) both; }
@keyframes vo-in { from { height: 0; opacity: 0; } }
.vo-orb { position: relative; width: var(--agui-voice-orb, 76px); height: var(--agui-voice-orb, 76px); padding: 0; border: 0; border-radius: 50%; overflow: hidden; cursor: pointer;
  background: linear-gradient(160deg, color-mix(in srgb, var(--agui-voice) 72%, var(--agui-voice-cloud)), var(--agui-voice) 70%);
  box-shadow: 0 8px 22px -8px color-mix(in srgb, var(--agui-voice) 70%, transparent); transform-origin: 50% 100%; transition: transform .33s var(--agui-ease), filter .33s; }
.vo-orb::before { content: ''; position: absolute; inset: -30%; background: conic-gradient(from 0deg, transparent 0 38%, color-mix(in srgb, var(--agui-voice-cloud) 95%, transparent) 52% 78%, transparent 92%); filter: blur(9px); animation: vo-turn 4s linear infinite; }
.vo-orb::after { content: ''; position: absolute; inset: 0; border-radius: 50%; box-shadow: inset 0 0 10px color-mix(in srgb, var(--agui-voice-cloud) 55%, transparent); }
.vo-orb:focus-visible { outline: 2px solid var(--agui-voice); outline-offset: 3px; }
.vo-orb svg { position: absolute; inset: 0; margin: auto; z-index: 1; color: var(--agui-on-voice); opacity: 0; transition: opacity .15s; }
.vo-think .vo-orb, .vo-wait .vo-orb { transform: translateY(-8px) scale(.9); }
.vo-think .vo-orb::before, .vo-wait .vo-orb::before { animation-duration: 2.6s; }
.vo-think .vo-orb svg, .vo-speak .vo-orb svg { opacity: .9; }   /* a press stops this answer: the mark is there on a phone too */
.vo-speak .vo-orb::before { animation-duration: 2.7s; }
.vo-silent .vo-orb { transform: scale(.66); filter: grayscale(1) brightness(.85); }
.vo-silent .vo-orb::before { animation: none; }
.vo-step { height: 18px; max-width: 100%; font: 13px/18px var(--agui-font); color: var(--agui-ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@keyframes vo-turn { to { transform: rotate(360deg); } }
/* the turn's step is said under the orb: the conversation's own live line keeps its place, unseen, until it is done */
.panel:has(.foot.vo-on) .log > .steps:not(.done) { visibility: hidden; }
/* the row: the composer, then the microphone and the close button; while a message is typed the close button steps
   aside, the microphone stays within reach */
.foot.vo-on { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; column-gap: 8px; align-items: end; }
.foot.vo-on > * { grid-column: 1 / -1; }
.foot.vo-on > .box { grid-column: 1; }
.foot.vo-on .box > .mic, .foot.vo-on .box > .send.idle, .foot.vo-ready .box > .mic { display: none; }
.foot.vo-on > .vo-b { grid-column: auto; }
.foot.vo-on.vo-typing > .box { grid-column: 1 / 3; }
.foot.vo-on.vo-typing > .vo-mic { grid-column: 3; }
.foot.vo-on.vo-typing > .vo-x { display: none; }
.foot.vo-on .box > .send:not(.idle) { background: var(--agui-voice); color: var(--agui-on-voice); }
.vo-b { width: 40px; height: 40px; margin-bottom: 7px; padding: 0; border: 0; border-radius: 50%; display: grid; place-items: center; cursor: pointer; background: var(--agui-soft); color: var(--agui-ink); }
.vo-b.on { background: color-mix(in srgb, var(--agui-danger) 16%, var(--agui-bg)); color: var(--agui-danger-ink); }   /* the microphone is off */
.vo-x { background: var(--agui-knob); color: var(--agui-voice-close-ink, #1d1d1f); box-shadow: 0 2px 10px -2px var(--agui-shadow), 0 0 0 1px var(--agui-line-2); }
@media (pointer: coarse) { .vo-b { width: 48px; height: 48px; } }
/* before voice: a small, slow orb in the message box, where the microphone was */
.vo-go { flex: none; align-self: flex-end; width: 36px; height: 36px; padding: 0; border: 0; border-radius: 50%; background: none; display: grid; place-items: center; cursor: pointer; }
.vo-go i { position: relative; width: 26px; height: 26px; border-radius: 50%; overflow: hidden; background: linear-gradient(160deg, color-mix(in srgb, var(--agui-voice) 72%, var(--agui-voice-cloud)), var(--agui-voice) 70%); }
.vo-go i::before { content: ''; position: absolute; inset: -30%; background: conic-gradient(from 0deg, transparent 0 38%, color-mix(in srgb, var(--agui-voice-cloud) 95%, transparent) 52% 78%, transparent 92%); filter: blur(4px); animation: vo-turn 9s linear infinite; }
@media (pointer: coarse) { .vo-go { width: 44px; height: 44px; } }
.foot.vo-on .vo-go { display: none; }
.vo-hearing .bubble { color: var(--agui-ink-2); }   /* still being heard */
/* the code: a sheet from the bottom of the chat; a narrow card in a wide one */
.vo-veil { position: absolute; inset: 0; z-index: 7; background: var(--agui-scrim); animation: vo-fade .2s ease both; }
.vo-sheet { position: absolute; left: 0; right: 0; bottom: 0; z-index: 8; display: grid; gap: 12px; box-sizing: border-box; padding: 20px 20px max(20px, env(safe-area-inset-bottom));
  border-radius: var(--agui-radius-lg) var(--agui-radius-lg) 0 0; background: var(--agui-sheet-bg, var(--agui-bg)); color: var(--agui-ink); font: 15px/1.45 var(--agui-font);
  box-shadow: 0 -10px 40px -12px var(--agui-shadow); animation: vo-up .24s var(--agui-ease) both; }
@media (min-width: 761px) { .vo-sheet { max-width: 420px; margin-inline: auto; bottom: 24px; padding-bottom: 20px; border-radius: var(--agui-radius-lg); } }
:host(.dark) .vo-sheet { background: var(--agui-sheet-bg, var(--agui-surface)); }
.vo-sheet b { font: 600 17px/1.3 var(--agui-font); }
.vo-sheet p { margin: -8px 0 0; color: var(--agui-ink-2); font-size: 13px; }
.vo-sheet input { width: 100%; min-height: 44px; box-sizing: border-box; border: 1px solid transparent; border-radius: var(--agui-radius-sm); padding: 10px 14px; font: 16px/1.3 var(--agui-font);
  letter-spacing: .08em; background: var(--agui-soft); color: var(--agui-ink); outline: none; }
.vo-sheet input::placeholder { color: var(--agui-ink-3); letter-spacing: 0; }
.vo-sheet input:focus-visible { border-color: var(--agui-voice); box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-voice) 20%, transparent); }
.vo-sheet.bad input { animation: vo-shake .3s; border-color: var(--agui-danger); }
.vo-sheet.bad input:focus-visible { box-shadow: 0 0 0 3px color-mix(in srgb, var(--agui-danger) 20%, transparent); }
.vo-err { min-height: 18px; margin: -8px 0; font-size: 13px; color: var(--agui-danger-ink); }
.vo-sheet button { min-height: 44px; border: 0; border-radius: var(--agui-radius-pill); font: 600 15px var(--agui-font); cursor: pointer; background: var(--agui-accent); color: var(--agui-on-accent); }
.vo-sheet button:disabled { opacity: .35; cursor: default; }
.vo-sheet.busy button[type=submit] { opacity: .6; }
.vo-sheet button.q { background: none; color: var(--agui-ink-2); font-weight: 400; }
@keyframes vo-up { from { transform: translateY(100%); } }
@keyframes vo-fade { from { opacity: 0; } }
@keyframes vo-shake { 25% { transform: translateX(-6px); } 75% { transform: translateX(6px); } }
@media (prefers-reduced-motion: reduce) { .vo-orb::before, .vo-go i::before, .vo-sheet, .vo-veil, .vo-dock, .vo-sheet.bad input { animation: none; } .vo-orb { transition: none; } }`

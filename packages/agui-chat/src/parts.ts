/**
 * The styling vocabulary: every element the chat draws gets a `part` name from this map, so a page can style it
 * with agui-chat::part(name) and a theme's css with [part~="name"]. Class names stay internal; these names are
 * the public, stable API (documented on the themes page). Elements that appear later (a card's result line, a
 * calendar opened in a card) get their parts from a MutationObserver.
 */
export const PARTS: [string, string][] = [
  // chrome
  ['.panel', 'panel'], ['.scrim', 'scrim'], ['.fab', 'fab'], ['.fab-dot', 'unread'], ['.greet', 'greeting'], ['.head', 'header'], ['.logo', 'logo'], ['.title', 'title'],
  ['.sub', 'subtitle'], ['.head .icon', 'icon-button'], ['.close', 'close'], ['.log', 'log'],
  ['.empty', 'empty'], ['.empty h3', 'empty-title'], ['.empty p', 'empty-intro'],
  ['.msg', 'message'], ['.msg.me', 'user'], ['.msg.me > div', 'user-bubble'], ['.msg.ai', 'assistant'], ['.msg .body', 'message-body'],
  ['.steps', 'steps'], ['.steps > button', 'steps-toggle'], ['.steps li', 'step'],
  ['.quick', 'suggestions'], ['.wait', 'typing'], ['.notice', 'notice'], ['.error', 'error'],
  ['.foot', 'composer'], ['.box', 'composer-box'], ['.box textarea', 'input'], ['.send', 'send'], ['.mic', 'mic'],
  ['.clip', 'attach'], ['.files', 'attachments'], ['.hint', 'hint'],
  ['.sel-cap', 'selection-menu'], ['.sel-pop', 'reply-window'], ['.reply-list', 'reply'], ['.reply-chip', 'reply-quote'], ['.bubble-q', 'message-quote'], ['.fold-btn', 'fold-toggle'],
  // shared controls
  ['.chip', 'chip'], ['.chip.act', 'action-chip'], ['.chip.on', 'chip-selected'],
  ['.btn', 'button'], ['.btn.pri', 'button-primary'], ['.btn.sec', 'button-secondary'], ['.btn.link', 'button-link'],
  ['.btn.danger', 'button-danger'], ['.acts', 'actions'], ['.ok-line', 'result'], ['.tag', 'tag'],
  ['.text-in', 'text-input'], ['.num', 'number'], ['.num-step', 'number-stepper'], ['.num-b', 'number-step'],
  ['.sel', 'select'], ['.field', 'editor'],
  // cards
  ['.card-q', 'card-question'], ['.card-t', 'card-title'], ['.card-msg', 'card-message'],
  ['.row', 'row'], ['.row-label', 'row-label'], ['.row-main > div > b', 'row-value'], ['.row-tools', 'row-tools'],
  ['.was', 'row-previous'], ['.issue-line', 'row-issue'], ['.shared', 'card-reason'], ['.doc-head', 'document'],
  ['.fold', 'fold'], ['.opt', 'option'], ['.opts', 'options'], ['.cmp', 'comparison'], ['.cmp-col', 'comparison-column'],
  ['.search', 'search'], ['.strip', 'day-strip'], ['.slots', 'slots'], ['.range', 'range'], ['.range input', 'slider'],
  ['.range-p', 'range-preview'], ['.stepper', 'stepper'], ['.fields', 'fields'], ['.fld', 'fields-item'],
  ['.date-face', 'date-field'], ['.cal', 'calendar'], ['.cal-title', 'calendar-title'], ['.cal-nav', 'calendar-nav'],
  ['.cal-wd', 'calendar-weekday'], ['.cal-d', 'calendar-day'], ['.cal-d.on', 'calendar-day-selected'],
  ['.cal-d.today', 'calendar-today'], ['.cal-y', 'calendar-cell'],
  ['.rev', 'review'], ['.rev-s', 'review-section'], ['.row.issue', 'review-issue'],
  ['.srcs', 'sources'], ['.src-chip', 'source'], ['.receipt', 'receipt'], ['.feedback', 'feedback'],
  ['.details', 'details'], ['.consequence', 'consequence'], ['.zone', 'dropzone'], ['.bar', 'progress'], ['.privacy', 'privacy'],
]

/** Every part name, for docs and tests. */
export const PART_NAMES = [...new Set(PARTS.map(([, p]) => p))]

/** Parts that follow a state class (they go when the class goes). */
const STATES = new Set(['chip-selected', 'calendar-day-selected', 'action-chip'])

function tag(el: Element): void {
  let now = (el.getAttribute('part') ?? '').split(/\s+/).filter(Boolean)
  const before = now.join(' ')
  for (const [sel, part] of PARTS) {
    const hit = el.matches(sel)
    if (hit && !now.includes(part)) now.push(part)
    else if (!hit && STATES.has(part)) now = now.filter((p) => p !== part)
  }
  const after = now.join(' ')
  if (after !== before) { if (after) el.setAttribute('part', after); else el.removeAttribute('part') }
}

/** Add parts to `root` and everything in it. */
export function addParts(root: Element | ShadowRoot): void {
  if (root instanceof Element) tag(root)
  root.querySelectorAll('*').forEach(tag)
}

/** Keep adding parts as elements appear (cards change after an answer, a calendar opens in place). */
export function watchParts(root: ShadowRoot): MutationObserver {
  addParts(root)
  const mo = new MutationObserver((records) => {
    for (const r of records) {
      r.addedNodes.forEach((n) => { if (n instanceof Element) addParts(n) })
      if (r.type === 'attributes' && r.target instanceof Element) tag(r.target)
    }
  })
  mo.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] })
  return mo
}

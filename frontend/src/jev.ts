/** The demo's "Decision model (Jev) · experimental" switch in the chat's "+" menu (the owner's decision: an
 * experimental feature behind an access code, like the voice mode). Without a code nothing is sent to the decision
 * model's supplier: the server gets no pass and keeps the layer off for this visitor.
 *
 * States, as the voice mode: no code ("Needs your code") → the code sheet (wrong code / no connection / not here);
 * a code → on ("On"; a tap turns it off) / off ("Off"; a tap turns it on). The pass lives in this tab's session only
 * and goes as a header on the chat's own requests. The server's names come from Owner TL: POST {base}/unlock {code}
 * → {pass} (403 wrong code, 404 not on this host), header X-Jev-Pass; until his gate is live the row says the code
 * could not be checked. */
import type { AguiChatElement } from '@formguide/agui-chat'

const ID = 'jev'
const KEY = 'jev-pass', ON = 'jev-on'
// a small decision fork on the 24 grid, as the menu's other glyphs (stroke)
const ICON = 'M12 3v6M12 9l-6 6M12 9l6 6M6 15v4M18 15v4'
const W = {
  menu: 'Decision model (Jev)', needs: 'Experimental · needs your code', on: 'Experimental · on', off: 'Experimental · off',
  intro: 'A small model reads your line first and does simple things itself, faster. It is a trial. Enter your personal access code.',
  code: 'Access code', activate: 'Turn on', notNow: 'Not now',
  bad: 'That code did not work', none: 'The decision model is not available here', noConnect: 'Could not connect. Try again.',
  noCheck: 'Could not check the code. Try again.',
}

const read = (k: string): string => { try { return sessionStorage.getItem(k) ?? '' } catch { return '' } }
const write = (k: string, v: string): void => { try { if (v) sessionStorage.setItem(k, v); else sessionStorage.removeItem(k) } catch { /* private mode */ } }

/** Puts the row into the chat's "+" menu and keeps the pass on the chat's requests. `base`: the server's route
 *  (by default /jev on the chat's own host). Returns a function that removes everything again. */
export function jevSwitch(chat: AguiChatElement, host: HTMLElement, base = '/jev'): () => void {
  let pass = read(KEY), on = !!pass && read(ON) !== '0'
  const row = (): void => {
    const others = (chat.options.menu ?? []).filter((m) => m.id !== ID)
    chat.options = { menu: [...others, { id: ID, label: W.menu, hint: !pass ? W.needs : on ? W.on : W.off, icon: ICON }] }
  }
  // the pass on every request of the chat (its runs and its uploads), only while on
  const before = chat.options.headers
  chat.options = { headers: async (req: { kind: string; url: string }) => {
    const own = typeof before === 'function' ? await before(req) : before
    return { ...(own ?? {}), ...(pass && on ? { 'X-Jev-Pass': pass } : {}) }
  } }
  row()
  // the voice row arrives a moment later and appends itself: until then this row is put back last, so the menu reads
  // files, voice, decision model (a few checks in the first seconds; nothing runs after)
  let checks = 0
  const keepLast = setInterval(() => {
    const m = chat.options.menu ?? []
    if (m.length && m[m.length - 1].id !== ID) row()
    if (++checks >= 12) clearInterval(keepLast)
  }, 500)

  const sheet = (): void => {
    if (host.querySelector('.jev-sheet')) return
    const veil = document.createElement('div'); veil.className = 'jev-veil'
    const s = document.createElement('form'); s.className = 'jev-sheet'
    s.setAttribute('role', 'dialog'); s.setAttribute('aria-modal', 'true'); s.setAttribute('aria-label', W.menu)
    s.innerHTML = `<b></b><p></p><input type="text" autocomplete="off" autocapitalize="characters" spellcheck="false"><div class="jev-err" role="alert"></div><button type="submit" disabled></button><button type="button" class="q"></button>`
    const [title, intro] = [s.querySelector('b')!, s.querySelector('p')!]
    const code = s.querySelector('input')!, err = s.querySelector<HTMLElement>('.jev-err')!
    const [ok, no] = [...s.querySelectorAll('button')] as HTMLButtonElement[]
    title.textContent = W.menu; intro.textContent = W.intro; code.placeholder = W.code; code.setAttribute('aria-label', W.code); ok.textContent = W.activate; no.textContent = W.notNow
    const shut = (): void => { document.removeEventListener('keydown', key, true); veil.remove(); s.remove() }
    const key = (e: KeyboardEvent): void => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); shut() } }
    code.addEventListener('input', () => { ok.disabled = !code.value.trim(); s.classList.remove('bad'); code.removeAttribute('aria-invalid'); err.textContent = '' })
    no.addEventListener('click', shut); veil.addEventListener('click', shut)
    s.addEventListener('submit', async (e) => {
      e.preventDefault()
      if (ok.disabled) return
      ok.disabled = true; s.classList.add('busy')
      let r: Response | null = null
      try { r = await fetch(`${base}/unlock`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code.value.trim() }) }) } catch { /* no connection */ }
      s.classList.remove('busy')
      if (r?.ok) {
        pass = String(((await r.json().catch(() => ({}))) as { pass?: string }).pass ?? '')
        if (pass) { on = true; write(KEY, pass); write(ON, '1'); shut(); row(); return }
      }
      err.textContent = !r ? W.noConnect : r.status === 404 ? W.none : r.status === 403 ? W.bad : W.noCheck
      if (r?.status === 403) { s.classList.add('bad'); code.setAttribute('aria-invalid', 'true'); code.select() }
      ok.disabled = !code.value.trim()
    })
    document.addEventListener('keydown', key, true)
    host.append(veil, s)
    code.focus({ preventScroll: true })
  }

  const act = (e: Event): void => {
    if ((e as CustomEvent).detail?.id !== ID) return
    e.preventDefault()
    if (!pass) { sheet(); return }
    on = !on; write(ON, on ? '1' : '0'); row()   // a tap turns it on or off; the next turn follows
  }
  chat.addEventListener('agui:menu-action', act)
  return () => {
    chat.removeEventListener('agui:menu-action', act)
    clearInterval(keepLast)
    chat.options = { menu: (chat.options.menu ?? []).filter((m) => m.id !== ID), headers: before }
  }
}

/** The server said the pass ran out (a 403 with this reason on a run): forget it, so the row asks for the code again. */
export function jevExpired(chat: AguiChatElement): void { write(KEY, ''); write(ON, ''); chat.dispatchEvent(new CustomEvent('jev:expired')) }

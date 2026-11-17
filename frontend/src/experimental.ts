/** The demo's one "Experimental" item in the chat's "+" menu (the owner: «two in one under one option in menu»):
 * one access code, then a switch for each experimental feature this code opens: the voice mode and the decision model
 * (Jev), each turned on on its own. Without a code: only the code field. Nothing goes to the decision model's
 * supplier unless its switch is on: only then does the pass go with the chat's requests.
 *
 * The server's contract (Owner TL, ba371f6): GET {base} → {features, unlocked} (404: no gate on this host, the voice
 * mode keeps its own row as before); POST {base}/unlock {code} → {passes: {decision_model?, voice?}} (403: wrong code);
 * the decision model is on while X-Experiment-Pass: <passes.decision_model> goes with each run; the voice pass is the
 * one the voice mode takes from /voice/unlock. GET {base} with the header says whether a kept pass is still good. */
import type { AguiChatElement } from '@formguide/agui-chat'

const ID = 'experimental', HEADER = 'X-Experiment-Pass'
const PASSES = 'exp-passes', JEV_ON = 'exp-jev-on', VOICE_PASS = 'agui-voice-pass'   // the last is the voice mode's own key
// a flask, the menu's line style on the 24 grid
const ICON = 'M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3M7.5 14h9'
const W = {
  menu: 'Experimental', needs: 'Needs your code', on: (n: string) => `${n} on`, none: 'All off',
  intro: 'Features we are trying out. They can make mistakes. Enter your personal access code.',
  code: 'Access code', activate: 'Activate', notNow: 'Not now', done: 'Done',
  voice: 'Voice mode', voiceHint: 'Talk instead of typing', jev: 'Decision model (Jev)', jevHint: 'Reads your line first and does simple things itself',
  bad: 'That code did not work', noConnect: 'Could not connect. Try again.', noCheck: 'Could not check the code. Try again.',
}
type Passes = { decision_model?: string; voice?: string }

const read = (k: string): string => { try { return sessionStorage.getItem(k) ?? '' } catch { return '' } }
const write = (k: string, v: string): void => { try { if (v) sessionStorage.setItem(k, v); else sessionStorage.removeItem(k) } catch { /* private mode */ } }
const readPasses = (): Passes => { try { return JSON.parse(read(PASSES) || '{}') as Passes } catch { return {} } }

/** Puts the item into the chat's "+" menu on a host with the gate. `voice`: whether this page has the voice mode. */
export function experimental(chat: AguiChatElement, host: HTMLElement, voice: boolean, base = '/experiments'): () => void {
  let passes = readPasses(), jevOn = !!passes.decision_model && read(JEV_ON) === '1', offered = false
  const hasVoice = (): boolean => voice || !!(chat.options as { voiceMode?: boolean }).voiceMode   // the page may turn voice on a moment later
  const voiceOn = (): boolean => !!read(VOICE_PASS)
  const tellVoice = (): void => { chat.dispatchEvent(new CustomEvent('agui:voice-pass')) }
  const hint = (): string => {
    if (!passes.decision_model && !passes.voice) return W.needs
    const on = [hasVoice() && passes.voice && voiceOn() ? W.voice : '', jevOn ? 'Jev' : ''].filter(Boolean)
    return on.length ? W.on(on.join(', ')) : W.none
  }
  const row = (): void => {
    const others = (chat.options.menu ?? []).filter((m) => m.id !== ID && m.id !== 'agui-voice')
    chat.options = { menu: offered ? [...others, { id: ID, label: W.menu, hint: hint(), icon: ICON }] : (chat.options.menu ?? []).filter((m) => m.id !== ID) }
  }
  // the decision model's pass on every request of the chat, only while its switch is on
  const before = chat.options.headers
  chat.options = { headers: async (req: { kind: string; url: string }) => {
    const own = typeof before === 'function' ? await before(req) : before
    return { ...(own ?? {}), ...(jevOn && passes.decision_model ? { [HEADER]: passes.decision_model } : {}) }
  } }
  // a host with the gate: one item for everything experimental (the voice mode stops adding its own row)
  void fetch(base, { headers: passes.decision_model ? { [HEADER]: passes.decision_model } : {} }).then(async (r) => {
    if (!r.ok) return   // no gate here: the voice mode keeps its own row
    const d = (await r.json().catch(() => ({}))) as { features?: string[]; unlocked?: boolean }
    if (!d.features?.length) return
    if (passes.decision_model && d.unlocked === false) { passes = {}; jevOn = false; write(PASSES, ''); write(JEV_ON, ''); write(VOICE_PASS, ''); tellVoice() }
    chat.setAttribute('data-voice-menu', 'off')
    offered = true; row()
  }, () => {})
  // the voice row may arrive a moment later: it is taken out again (a few checks in the first seconds)
  let checks = 0
  const keep = setInterval(() => { if (offered && (chat.options.menu ?? []).some((m) => m.id === 'agui-voice')) row(); if (++checks >= 12) clearInterval(keep) }, 500)

  const veil = (): HTMLElement => { const v = document.createElement('div'); v.className = 'jev-veil'; return v }
  const close = (): void => { host.querySelectorAll('.jev-veil, .jev-sheet').forEach((x) => x.remove()); document.removeEventListener('keydown', esc, true) }
  const esc = (e: KeyboardEvent): void => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close() } }
  const open = (s: HTMLElement): void => { close(); const v = veil(); v.addEventListener('click', close); host.append(v, s); document.addEventListener('keydown', esc, true) }

  /** The switches: one per feature this code opens, each on its own. */
  const switches = (): void => {
    const s = document.createElement('div'); s.className = 'jev-sheet'
    s.setAttribute('role', 'dialog'); s.setAttribute('aria-modal', 'true'); s.setAttribute('aria-label', W.menu)
    const title = document.createElement('b'); title.textContent = W.menu
    const list = document.createElement('div'); list.className = 'exp-list'
    const add = (label: string, sub: string, get: () => boolean, set: (v: boolean) => void): void => {
      const row = document.createElement('label'); row.className = 'exp-row'
      const text = document.createElement('span'); text.innerHTML = '<span class="exp-n"></span><span class="exp-h"></span>'
      text.querySelector('.exp-n')!.textContent = label; text.querySelector('.exp-h')!.textContent = sub
      const sw = document.createElement('input'); sw.type = 'checkbox'; sw.setAttribute('role', 'switch'); sw.className = 'exp-sw'; sw.checked = get()
      sw.addEventListener('change', () => { set(sw.checked); row.classList.toggle('on', sw.checked) })
      row.classList.toggle('on', sw.checked); row.append(text, sw); list.append(row)
    }
    if (hasVoice() && passes.voice) add(W.voice, W.voiceHint, voiceOn, (v) => { write(VOICE_PASS, v ? passes.voice! : ''); tellVoice(); row() })
    if (passes.decision_model) add(W.jev, W.jevHint, () => jevOn, (v) => { jevOn = v; write(JEV_ON, v ? '1' : ''); row() })
    const done = document.createElement('button'); done.type = 'button'; done.textContent = W.done; done.addEventListener('click', close)
    s.append(title, list, done)
    open(s)
    list.querySelector<HTMLInputElement>('input')?.focus({ preventScroll: true })
  }

  /** The code: one for everything; what it opens comes back as passes. */
  const sheet = (): void => {
    const s = document.createElement('form'); s.className = 'jev-sheet'
    s.setAttribute('role', 'dialog'); s.setAttribute('aria-modal', 'true'); s.setAttribute('aria-label', W.menu)
    s.innerHTML = '<b></b><p></p><input type="text" autocomplete="off" autocapitalize="characters" spellcheck="false"><div class="jev-err" role="alert"></div><button type="submit" disabled></button><button type="button" class="q"></button>'
    s.querySelector('b')!.textContent = W.menu; s.querySelector('p')!.textContent = W.intro
    const code = s.querySelector('input')!, err = s.querySelector<HTMLElement>('.jev-err')!
    const [ok, no] = [...s.querySelectorAll('button')] as HTMLButtonElement[]
    code.placeholder = W.code; code.setAttribute('aria-label', W.code); ok.textContent = W.activate; no.textContent = W.notNow
    code.addEventListener('input', () => { ok.disabled = !code.value.trim(); s.classList.remove('bad'); code.removeAttribute('aria-invalid'); err.textContent = '' })
    no.addEventListener('click', close)
    s.addEventListener('submit', async (e) => {
      e.preventDefault()
      if (ok.disabled) return
      ok.disabled = true; s.classList.add('busy')
      let r: Response | null = null
      try { r = await fetch(`${base}/unlock`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code.value.trim() }) }) } catch { /* no connection */ }
      s.classList.remove('busy')
      if (r?.ok) {
        const d = (await r.json().catch(() => ({}))) as { passes?: Passes }
        passes = { ...(d.passes?.decision_model ? { decision_model: d.passes.decision_model } : {}), ...(d.passes?.voice ? { voice: d.passes.voice } : {}) }
        if (passes.decision_model || passes.voice) { write(PASSES, JSON.stringify(passes)); row(); switches(); return }   // the code is in: the switches
      }
      err.textContent = !r ? W.noConnect : r.status === 403 || r.ok ? W.bad : W.noCheck
      if (r?.status === 403 || r?.ok) { s.classList.add('bad'); code.setAttribute('aria-invalid', 'true'); code.select() }
      ok.disabled = !code.value.trim()
    })
    open(s)
    code.focus({ preventScroll: true })
  }

  const act = (e: Event): void => {
    if ((e as CustomEvent).detail?.id !== ID) return
    e.preventDefault()
    if (passes.decision_model || passes.voice) switches(); else sheet()
  }
  chat.addEventListener('agui:menu-action', act)
  return () => {
    chat.removeEventListener('agui:menu-action', act); clearInterval(keep); close()
    chat.removeAttribute('data-voice-menu')
    chat.options = { menu: (chat.options.menu ?? []).filter((m) => m.id !== ID), headers: before }
  }
}

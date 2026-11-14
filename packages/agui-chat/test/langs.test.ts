import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'
import { STRINGS } from '../src/i18n'
import { FG_STRINGS, TOOL_LABELS } from '../src/formguide/i18n'
import { LANGUAGES, PACKS, addLanguage, loadLanguage } from '../src/langs'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
async function mount(lang: string): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', 'persist-thread': 'off', lang, url: '/agent/run' })) el.setAttribute(k, v)
  document.body.appendChild(el)
  await tick()
  return el
}

beforeEach(() => { document.body.innerHTML = ''; vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 }))) })
afterEach(() => { vi.unstubAllGlobals() })

describe('language packs', () => {
  it('every pack has every English text', async () => {
    for (const l of LANGUAGES) {
      expect(await loadLanguage(l)).toBe(true)
      // a pack may have more (plural forms: field_few, field_many), never less
      const missing = (have: Record<string, string> | undefined, en: Record<string, string>) => Object.keys(en).filter((k) => !(k in (have ?? {})))
      expect(missing(PACKS[l].core, STRINGS.en)).toEqual([])
      expect(missing(PACKS[l].formguide, FG_STRINGS.en)).toEqual([])
      expect(missing(PACKS[l].tools, TOOL_LABELS.en)).toEqual([])
    }
  })

  it('a chat in German switches to German when its pack arrives', async () => {
    delete PACKS.de
    const el = await mount('de')
    await loadLanguage('de')
    await tick()
    expect(el.lang).toBe('de')
    expect(el.shadowRoot!.querySelector('textarea')!.getAttribute('placeholder')).toBe(PACKS.de.core!.placeholder)
  })

  it('stays in English for a language without a pack, and takes a pack of your own', async () => {
    const el = await mount('pt')
    expect(await loadLanguage('pt')).toBe(false)
    expect(el.lang).toBe('en')
    addLanguage('pt', { core: { placeholder: 'Escreva ao assistente' } })
    el.options = { lang: 'pt' }
    expect(el.lang).toBe('pt')
    expect(el.t('placeholder')).toBe('Escreva ao assistente')
    expect(el.t('send')).toBe('Send')   // missing texts fall back to English
  })
})

describe('the conversation\'s language', () => {
  it('cards and the steps line follow the language the server names; the frame stays the page\'s', async () => {
    const { formguide } = await import('../src/formguide/index')
    const el = document.createElement('agui-chat') as AguiChatElement
    for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
    document.body.appendChild(el)
    el.use(formguide({ getState: () => ({ config: { props: {}, state: {} }, jsx_hash: 'h' }), applyChanges: async () => ({}) }))
    await new Promise((r) => setTimeout(r))
    el.agent = { run: () => ({ subscribe: (o: { next: (e: unknown) => void; complete: () => void }) => {
      setTimeout(() => {
        for (const e of [{ type: 'RUN_STARTED', threadId: 't', runId: 'r' }, { type: 'CUSTOM', name: 'language', value: { lang: 'de' } },
          { type: 'TOOL_CALL_START', toolCallId: 'a', toolCallName: 'ask_documents' }, { type: 'TOOL_CALL_END', toolCallId: 'a' },
          { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'ask', card_id: 'q', question: 'Welche Versicherung?', language: 'de',
            options: [{ id: 'a', label: 'Haftpflicht' }], multiple: false, allow_text: true }) },
          { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }]) o.next(e)
        o.complete()
      })
      return { unsubscribe() {} }
    } }) } as never
    await el.send('Ich brauche eine Versicherung')
    await new Promise((r) => setTimeout(r, 300))
    const root = el.shadowRoot!
    const skip = [...root.querySelectorAll<HTMLButtonElement>('.card .btn.link')].map((b) => b.textContent)
    expect(skip).toContain('\u00dcberspringen')                                   // the card's own words: German
    expect(root.querySelector('.steps-t')!.textContent).toMatch(/^Fertig in/)      // the steps line too
    expect(root.querySelector('.title')!.textContent).toBe('Assistant')            // the frame: the page's English
    expect(root.querySelector('textarea')!.placeholder).toBe('Message the assistant\u2026')
  })
})

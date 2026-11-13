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

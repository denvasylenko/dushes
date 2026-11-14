/**
 * Languages: English is built in; the others are packs loaded the first time a chat needs one.
 * A pack holds the chat's own texts (core), the formguide cards' texts and the step labels of its tools.
 *   ES modules: a separate chunk per language, loaded with import() by the bundler.
 *   The one-script build: agui-chat.lang-<lang>.js next to agui-chat.iife.js, added with a <script> tag.
 * Your own texts (options.i18n, a plugin's i18n) always win over a pack.
 */
import { loadPack } from '#lang-loader'

export interface LangPack {
  core?: Record<string, string>
  formguide?: Record<string, string>
  tools?: Record<string, string>
}

/** The languages that ship as packs. */
export const LANGUAGES = ['ru', 'uk', 'de', 'fr', 'it', 'es']
export const PACKS: Record<string, LangPack> = {}
const loading = new Map<string, Promise<boolean>>()

/** Register a pack (also how a pack file registers itself); a language of your own works the same way. */
export function addLanguage(lang: string, pack: LangPack): void {
  const was = PACKS[lang] ?? {}
  PACKS[lang] = { core: { ...was.core, ...pack.core }, formguide: { ...was.formguide, ...pack.formguide }, tools: { ...was.tools, ...pack.tools } }
}

/** Load a shipped pack once; resolves true when the language is ready, false to stay in English. */
export function loadLanguage(lang: string): Promise<boolean> {
  if (lang === 'en' || PACKS[lang]) return Promise.resolve(true)
  if (!LANGUAGES.includes(lang)) return Promise.resolve(false)
  let p = loading.get(lang)
  if (!p) {
    p = loadPack(lang).then((pack) => { if (pack) addLanguage(lang, pack); return !!PACKS[lang] }, () => false)
      .finally(() => loading.delete(lang))   // only one load at a time; a pack removed later loads again
    loading.set(lang, p)
  }
  return p
}

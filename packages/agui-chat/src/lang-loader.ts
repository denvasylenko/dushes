/// <reference types="vite/client" />
/** Language packs for ES module builds: one chunk per language, loaded with import(). */
import type { LangPack } from './langs'

const files = import.meta.glob<{ default: LangPack }>('./lang/*.json')

export async function loadPack(lang: string): Promise<LangPack | null> {
  const file = files[`./lang/${lang}.json`]
  return file ? (await file()).default : null
}

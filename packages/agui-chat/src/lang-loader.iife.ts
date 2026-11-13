/** Packs for the one-script build: agui-chat.<kind>-<name>.js next to agui-chat.iife.js registers itself
 *  (AguiChat.addLanguage or AguiChat.defineTheme); the widget adds the file with a <script> tag. */
import type { LangPack } from './langs'

// where this script came from; read now, while it runs (document.currentScript is null later)
const base = (document.currentScript as HTMLScriptElement | null)?.src || ''

export function loadFile(file: string): Promise<null> {
  return new Promise((done, fail) => {
    if (!base) return fail(new Error('agui-chat: no script url'))
    const s = document.createElement('script')
    s.src = new URL(file, base).href
    s.onload = () => done(null)   // the file registered itself
    s.onerror = () => fail(new Error(s.src))   // the file is missing: stays English / default
    document.head.append(s)
  })
}

export const loadPack = (lang: string): Promise<LangPack | null> => loadFile(`agui-chat.lang-${lang}.js`)

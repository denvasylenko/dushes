/** Language packs for the one-script build: agui-chat.lang-<lang>.js next to agui-chat.iife.js registers itself. */
import type { LangPack } from './langs'

// where this script came from; read now, while it runs (document.currentScript is null later)
const base = (document.currentScript as HTMLScriptElement | null)?.src || ''

export function loadPack(lang: string): Promise<LangPack | null> {
  return new Promise((done, fail) => {
    if (!base) return fail(new Error('no script url'))
    const s = document.createElement('script')
    s.src = new URL(`agui-chat.lang-${lang}.js`, base).href
    s.onload = () => done(null)   // the file called AguiChat.addLanguage itself
    s.onerror = () => fail(new Error(`no ${s.src}`))
    document.head.append(s)
  })
}

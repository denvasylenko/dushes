// The one-script build's language packs: dist/agui-chat.lang-<lang>.js, each registers itself with
// AguiChat.addLanguage. The widget adds the one it needs with a <script> tag from next to agui-chat.iife.js.
import { readdirSync, readFileSync, writeFileSync } from 'node:fs'

const src = new URL('../src/lang/', import.meta.url)
for (const f of readdirSync(src).filter((n) => n.endsWith('.json'))) {
  const lang = f.replace(/\.json$/, '')
  const pack = JSON.stringify(JSON.parse(readFileSync(new URL(f, src), 'utf8')))
  writeFileSync(new URL(`../dist/agui-chat.lang-${lang}.js`, import.meta.url), `window.AguiChat&&window.AguiChat.addLanguage(${JSON.stringify(lang)},${pack});\n`)
}
// the same for the built-in theme packs: dist/agui-chat.theme-<name>.js calls AguiChat.defineTheme
const themes = new URL('../src/theme/', import.meta.url)
for (const f of readdirSync(themes).filter((n) => n.endsWith('.json'))) {
  const name = f.replace(/\.json$/, '')
  const theme = JSON.stringify(JSON.parse(readFileSync(new URL(f, themes), 'utf8')))
  writeFileSync(new URL(`../dist/agui-chat.theme-${name}.js`, import.meta.url), `window.AguiChat&&window.AguiChat.defineTheme(${JSON.stringify(name)},${theme});\n`)
}

/** Built-in theme packs for the one-script build: agui-chat.theme-<name>.js next to agui-chat.iife.js defines itself. */
import type { Theme } from './themes'
import { loadFile } from './lang-loader.iife'

export const loadThemePack = (name: string): Promise<Theme | null> => loadFile(`agui-chat.theme-${name}.js`)

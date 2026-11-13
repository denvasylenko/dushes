/// <reference types="vite/client" />
/** Built-in theme packs for ES module builds: one chunk per theme, loaded with import(). */
import type { Theme } from './themes'

const files = import.meta.glob<{ default: Theme }>('./theme/*.json')

export async function loadThemePack(name: string): Promise<Theme | null> {
  const file = files[`./theme/${name}.json`]
  return file ? (await file()).default : null
}

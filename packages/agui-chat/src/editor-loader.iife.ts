/** The image tools for the one-script build: agui-chat.editor.js next to agui-chat.iife.js registers them. */
import type { EditorOptions } from './editor'
import type { openZoom } from './zoom'
import { loadFile } from './lang-loader.iife'

type Tools = { openEditor: (o: EditorOptions) => void; openZoom: typeof openZoom }
const tools = (): Promise<Tools> => loadFile('agui-chat.editor.js').then(() => (globalThis as unknown as { AguiChat: Tools }).AguiChat)
export const loadEditor = (): Promise<(o: EditorOptions) => void> => tools().then((t) => t.openEditor)
export const loadZoom = (): Promise<typeof openZoom> => tools().then((t) => t.openZoom)

/** The markup editor for the one-script build: agui-chat.editor.js next to agui-chat.iife.js registers itself. */
import type { EditorOptions } from './editor'
import { loadFile } from './lang-loader.iife'

export const loadEditor = (): Promise<(o: EditorOptions) => void> => loadFile('agui-chat.editor.js')
  .then(() => (globalThis as unknown as { AguiChat: { openEditor: (o: EditorOptions) => void } }).AguiChat.openEditor)

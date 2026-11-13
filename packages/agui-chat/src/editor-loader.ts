/** The markup editor for ES module builds: its own chunk, loaded when the pencil is tapped. */
import type { EditorOptions } from './editor'

export const loadEditor = (): Promise<(o: EditorOptions) => void> => import('./editor').then((m) => m.openEditor)

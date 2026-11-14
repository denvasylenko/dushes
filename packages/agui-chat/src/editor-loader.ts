/** The image tools for ES module builds: their own chunk, loaded when an image is opened. */
import type { EditorOptions } from './editor'
import type { openZoom } from './zoom'

export const loadEditor = (): Promise<(o: EditorOptions) => void> => import('./editor').then((m) => m.openEditor)
export const loadZoom = (): Promise<typeof openZoom> => import('./media').then((m) => m.openZoom)

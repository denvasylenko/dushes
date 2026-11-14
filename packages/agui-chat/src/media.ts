/** The image tools, loaded together the first time an image is opened: the view (zoom.ts) and markup (editor.ts). */
export { openEditor } from './editor'
export { openZoom } from './zoom'
import { openZoom } from './zoom'

// the one-script build: agui-chat.editor.js registers both on window.AguiChat
const g = globalThis as unknown as { AguiChat?: Record<string, unknown> }
if (g.AguiChat) g.AguiChat.openZoom = openZoom

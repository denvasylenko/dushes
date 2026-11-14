/** Keyboard shortcuts written per platform: ⌘ ⌥ ⇧ ⌃ ↵ on a Mac, Ctrl, Alt, Shift, Enter as words elsewhere. Kept apart from
 *  the tooltip (tip.ts, loaded on demand) so the chat can name its keys for screen readers without it. */

const MAC_KEYS: Record<string, string> = { Mod: '⌘', Alt: '⌥', Shift: '⇧', Ctrl: '⌃', Enter: '↵', Esc: 'esc' }
const PC_KEYS: Record<string, string> = { Mod: 'Ctrl', Alt: 'Alt', Shift: 'Shift', Ctrl: 'Ctrl', Enter: 'Enter', Esc: 'Esc' }

/** A Mac (or an iPad with a keyboard): from userAgentData when the browser has it, else platform / the user agent. */
export function isMac(): boolean {
  if (typeof navigator === 'undefined') return false
  const n = navigator as Navigator & { userAgentData?: { platform?: string } }
  return /mac|iphone|ipad/i.test(n.userAgentData?.platform || n.platform || n.userAgent || '')
}

/** One key as the platform writes it: 'Mod' -> ⌘ on a Mac, Ctrl elsewhere; a letter in capitals. */
export function keyLabel(key: string, mac = isMac()): string {
  return (mac ? MAC_KEYS : PC_KEYS)[key] ?? key.toUpperCase()
}

/** The value for aria-keyshortcuts ("Shift+Enter", "Meta+D"). */
export function ariaKeys(keys: string[], mac = isMac()): string {
  return keys.map((k) => (k === 'Mod' ? (mac ? 'Meta' : 'Control') : k === 'Ctrl' ? 'Control' : k === 'Esc' ? 'Escape' : k)).join('+')
}

/**
 * Themes: a named set of tokens for both schemes, per-scheme overrides and optional scoped CSS.
 *
 *   defineTheme('acme', {
 *     tokens: { accent: '#0a7f6f', radius: '10px', font: '"Inter", sans-serif' },   // both schemes
 *     dark: { accent: '#4fd1c1', bg: '#0f1514' },                                    // the dark scheme only
 *     css: '.chip { font-weight: 600 }',                                              // inside the widget
 *   })
 *   <agui-chat theme="acme" scheme="auto">
 *
 * Layers, lowest first: the widget's defaults, the theme, then CSS on the element from the page
 * (agui-chat { --agui-accent: ... }, agui-chat[data-scheme="dark"] { ... }, ::part()).
 */
export type Tokens = Record<string, string>

export interface Theme {
  /** A registered theme this one starts from. Default: "default". */
  extends?: string
  /** Tokens for both schemes; keys with or without the --agui- prefix. */
  tokens?: Tokens
  light?: Tokens
  dark?: Tokens
  /** CSS scoped to the widget's shadow root (.msg.me, .card, .chip, ...). */
  css?: string
}

/** Every token the widget reads (without the --agui- prefix). */
export const TOKENS = [
  'accent', 'on-accent', 'link', 'bg', 'surface', 'soft', 'ink', 'ink-2', 'ink-3', 'line', 'line-2',
  'ok', 'on-ok', 'danger', 'on-danger', 'shadow', 'scrim', 'knob',
  'radius', 'radius-sm', 'radius-lg', 'radius-pill', 'panel-width', 'font', 'ease', 'fade',
  // component tokens: each falls back to the globals above
  'panel-bg', 'panel-ink', 'header-bg', 'header-ink', 'header-border', 'log-bg',
  'bubble-user-bg', 'bubble-user-ink', 'bubble-ai-ink', 'bubble-radius',
  'card-bg', 'card-ink', 'card-border', 'card-radius', 'card-padding',
  'button-bg', 'button-ink', 'button-radius', 'button-secondary-bg', 'button-secondary-ink', 'button-secondary-border',
  'chip-bg', 'chip-ink', 'chip-border', 'chip-radius', 'chip-on-bg', 'chip-on-ink',
  'option-bg', 'option-ink', 'option-border', 'option-radius',
  'input-bg', 'input-ink', 'input-border', 'input-radius', 'input-height',
  'composer-bg', 'composer-border', 'composer-radius', 'composer-area-bg',
  'calendar-on-bg', 'calendar-on-ink',
  'bubble-width', 'bubble-height', 'bubble-offset', 'bubble-window-radius', 'launcher-size',
] as const

const KNOWN = new Set<string>(TOKENS)
const registry = new Map<string, Theme>()
const warned = new Set<string>()

function warn(msg: string): void {
  if (warned.has(msg)) return
  warned.add(msg)
  console.warn(`agui-chat: ${msg}`)
}

/** "accent", "--accent" or "--agui-accent" -> "--agui-accent"; null for an unknown key. */
export function tokenName(key: string): string | null {
  const k = key.trim().replace(/^--/, '').replace(/^agui-/, '')
  if (KNOWN.has(k)) return `--agui-${k}`
  warn(`unknown theme token "${key}" (known: ${TOKENS.join(', ')})`)
  return null
}

/** Tokens -> CSS declarations; a value that could close the rule is dropped. */
function declarations(tokens: Tokens): string {
  const out: string[] = []
  for (const [k, v] of Object.entries(tokens)) {
    const name = tokenName(k)
    const value = String(v ?? '').trim()
    if (!name || !value) continue
    if (/[;{}]/.test(value)) { warn(`theme token "${k}" has a value with ; { or }: ignored`); continue }
    out.push(`${name}: ${value};`)
  }
  return out.join(' ')
}

/** Register (or replace) a theme; elements that use it re-apply at once. */
export function defineTheme(name: string, theme: Theme): void {
  if (!name || typeof name !== 'string') throw new Error('agui-chat: defineTheme needs a name')
  registry.set(name, theme)
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('agui:themes', { detail: name }))
}

/** The names of the registered themes. */
export const themes = (): string[] => [...registry.keys()]

export const hasTheme = (name: string): boolean => registry.has(name)

/** A theme with its `extends` chain merged (parents first). */
function resolve(theme: Theme, seen = new Set<Theme>()): Required<Omit<Theme, 'extends'>> {
  const out = { tokens: {} as Tokens, light: {} as Tokens, dark: {} as Tokens, css: '' }
  if (seen.has(theme)) return out
  seen.add(theme)
  const parentName = theme.extends ?? (theme === registry.get('default') ? undefined : 'default')
  const parent = parentName ? registry.get(parentName) : undefined
  if (parentName && !parent) warn(`theme extends unknown "${parentName}"`)
  if (parent) Object.assign(out, resolve(parent, seen))
  return {
    tokens: { ...out.tokens, ...theme.tokens },
    light: { ...out.light, ...theme.light },
    dark: { ...out.dark, ...theme.dark },
    css: [out.css, theme.css ?? ''].filter(Boolean).join('\n'),
  }
}

/** The CSS for a theme (a name or an object), to put after the widget's own styles. */
export function themeCss(theme: string | Theme | undefined): string {
  let t: Theme | undefined
  if (typeof theme === 'string') {
    t = registry.get(theme)
    if (!t) { warn(`unknown theme "${theme}": using "default" (define it with defineTheme)`); t = registry.get('default') }
  } else t = theme
  if (!t) return ''
  const r = resolve(t)
  const both = declarations(r.tokens)
  return `:host { ${both} ${declarations(r.light)} }\n:host(.dark) { ${both} ${declarations(r.dark)} }\n${r.css}`
}

// ---------------------------------------------------------------- built-in themes

/** Today's look: the defaults in styles.ts, nothing to add. */
defineTheme('default', {})

/** High contrast: pure black and white, stronger lines and text, a thicker focus ring. */
defineTheme('contrast', {
  extends: 'default',
  light: {
    accent: '#000', 'on-accent': '#fff', link: '#0040c0', ink: '#000', 'ink-2': '#1d1d1f', 'ink-3': '#3a3a3c',
    line: '#6e6e73', 'line-2': '#3a3a3c', ok: '#1b7f32', danger: '#c4001a', surface: '#fff', soft: '#ececf0',
  },
  dark: {
    accent: '#fff', 'on-accent': '#000', link: '#8cc4ff', bg: '#000', surface: '#0a0a0a', soft: '#1c1c1e', ink: '#fff',
    'ink-2': '#e5e5ea', 'ink-3': '#c7c7cc', line: '#8e8e93', 'line-2': '#aeaeb2', ok: '#4cd964', 'on-ok': '#000',
    danger: '#ff6961', 'on-danger': '#000',
  },
  css: `.card, .box, .chip, .btn.sec { border-width: 2px; }
button:focus-visible, input:focus-visible, select:focus-visible, [tabindex]:focus-visible { box-shadow: 0 0 0 3px var(--agui-link); }`,
})

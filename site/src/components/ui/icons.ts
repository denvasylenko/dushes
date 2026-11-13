/** The docs' icons (16 px grid, one stroke style); Icon.astro draws them, scripts use iconSvg(). */
export const ICONS = {
  copy: '<rect x="5.5" y="5.5" width="8" height="8" rx="2"/><path d="M10.5 5.5V4a1.5 1.5 0 0 0-1.5-1.5H4A1.5 1.5 0 0 0 2.5 4v5A1.5 1.5 0 0 0 4 10.5h1.5"/>',
  check: '<path d="M3.5 8.5 6.5 11.5 12.5 4.5"/>',
  chevron: '<path d="M6 3.5 10.5 8 6 12.5"/>',
  external: '<path d="M6.5 3.5h-3v9h9v-3M9.5 2.5h4v4M13.5 2.5 7.5 8.5"/>',
  sparkle: '<path d="M8 1.5l1.3 3.9 3.9 1.3-3.9 1.3L8 11.9 6.7 8 2.8 6.7l3.9-1.3z"/>',
  replay: '<path d="M3 8a5 5 0 1 0 1.6-3.7M3 2.5v2.8h2.8"/>',
  sidebar: '<rect x="2" y="2.8" width="12" height="10.4" rx="2.4"/><path d="M6 2.8v10.4"/>',
  compass: '<circle cx="8" cy="8" r="6"/><path d="M10.5 5.5 9 9 5.5 10.5 7 7z"/>',
  form: '<rect x="2.5" y="2" width="11" height="12" rx="2.4"/><path d="M5 5.5h6M5 8h6M5 10.5h3.5"/>',
  doc: '<path d="M4 1.75h5.25L12.5 5v9.25H4z"/><path d="M9 1.75V5.25h3.5M6 8.25h4.5M6 10.75h3"/>',
} as const
export type IconName = keyof typeof ICONS
export const FILLED: ReadonlySet<IconName> = new Set(['sparkle'])

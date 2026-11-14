// A Vite plugin: minifies the widget's CSS templates (src/styles.ts, src/formguide/blocks-css.ts, src/tip-css.ts) at build time, so the source keeps its
// comments and layout. Only comments and whitespace go; quoted strings (content: '...') stay as written.
export function minifyCss() {
  return {
    name: 'agui-minify-css',
    transform(code, id) {
      const file = id.replace(/\\/g, '/').split('?')[0]
      if (!['/src/styles.ts', '/src/formguide/blocks-css.ts', '/src/tip-css.ts'].some((f) => file.endsWith(f))) return null
      const start = code.indexOf('`')
      const end = code.lastIndexOf('`')
      if (start < 0 || end <= start) return null
      // comments first: an apostrophe in one ("the bubble's colour") would otherwise read as a string's start
      const css = code.slice(start + 1, end).replace(/\/\*[\s\S]*?\*\//g, '')
      const parts = css.split(/('(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")/)
      const min = parts.map((p, i) => (i % 2 ? p : p
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/\s+/g, ' ')
        .replace(/\s*([{};,])\s*/g, '$1'))).join('').replace(/;}/g, '}').trim()
      return { code: code.slice(0, start + 1) + min + code.slice(end), map: null }
    },
  }
}

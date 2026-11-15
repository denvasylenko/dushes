/** A docs entry as plain Markdown for llms.txt, llms-full.txt and <page>.md (what AI tools read). */
import { speedMarkdown } from './bench';
import { recipeFilesMarkdown, recipeResultMarkdown } from './recipes';
import type { CollectionEntry } from 'astro:content';

const fragments = import.meta.glob('../fragments/*.html', { query: '?raw', eager: true, import: 'default' }) as Record<string, string>;

const decode = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');

/** An HTML fragment -> readable Markdown: headings, paragraphs, list items, code; SVG diagrams dropped. */
export function htmlToText(html: string): string {
  return decode(html
    .replace(/<svg[\s\S]*?<\/svg>/g, '')
    .replace(/<pre[^>]*>([\s\S]*?)<\/pre>/g, (_m, c) => `\n\`\`\`\n${c.replace(/<[^>]+>/g, '')}\n\`\`\`\n`)
    .replace(/<h2[^>]*>([\s\S]*?)<\/h2>/g, '\n## $1\n')
    .replace(/<h3[^>]*>([\s\S]*?)<\/h3>/g, '\n### $1\n')
    .replace(/<li[^>]*>/g, '\n- ')
    .replace(/<(td|th)[^>]*>/g, ' | ')
    .replace(/<\/tr>/g, '\n')
    .replace(/<code>([\s\S]*?)<\/code>/g, '`$1`')
    .replace(/<a [^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g, '[$2]($1)')
    .replace(/<\/(p|figcaption|div|ul|table)>/g, '\n')
    .replace(/<[^>]+>/g, ''))
    .replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}

/** Example files a page includes with `import x from '…/public/examples/<file>?raw'` and shows with <Code code={x} />. */
const examples = import.meta.glob('../../public/examples/*', { query: '?raw', eager: true, import: 'default' }) as Record<string, string>;

/** One attribute of a component tag: name="value", or a bare name (true). */
const attr = (tag: string, name: string): string | true | undefined => {
  const m = tag.match(new RegExp(`\\s${name.replace('.', '\\.')}(?:="([^"]*)")?(?=[\\s/>])`))
  return m ? (m[1] ?? true) : undefined
}

/** A Parameter list (ui/ParamList + Param) -> the signature, a title line and one list line per entry. */
function paramsToMd(part: string): string {
  return part
    .replace(/^[ \t]*<ParamList\b[^>]*>/gm, (tag) => {
      const sig = attr(tag, 'signature'), kind = attr(tag, 'kind'), title = attr(tag, 'title')
      const head = typeof sig === 'string' ? `${typeof kind === 'string' ? `${kind}: ` : ''}\`${sig}\`\n\n` : ''
      return `${head}${title === '' ? '' : `**${typeof title === 'string' ? title : 'Parameters'}**\n`}`
    })
    .replace(/^[ \t]*<Param\b[^>]*>/gm, (tag) => {
      const type = attr(tag, 'type'), def = attr(tag, 'default')
      const bits = [typeof type === 'string' ? type : '', attr(tag, 'required') ? 'required' : '',
        typeof def === 'string' ? `default \`${def}\`` : '', attr(tag, 'deprecated') ? 'deprecated' : ''].filter(Boolean)
      return `- \`${attr(tag, 'name')}\`${bits.length ? ` (${bits.join(', ')})` : ''}: `
    })
    .replace(/^[ \t]*<Fragment\s+slot="returns"\s*>/gm, '\n**Returns:** ')
    .replace(/^[ \t]*<Fragment\s+slot="example"\s*>/gm, '\n**Example:**\n')
    // a Code panel given its code inline: the code itself, as a code block
    .replace(/^[ \t]*<CodePanel\b([^>]*?)code=\{`([^`]*)`\}[^>]*\/>/gm, (_m, a, code) => {
      const label = attr(` ${a}`, 'label')
      return `\`\`\`${typeof label === 'string' ? label : ''}\n${code}\n\`\`\``
    })
    .replace(/[ \t]*<\/(ParamList|Param)>/g, '')
}

/** The components of one prose part (never inside a code block) -> Markdown equivalents. */
function proseToMd(part: string, raw: Record<string, string>): string {
  const stash: string[] = []
  return paramsToMd(part)
    .replace(/<Arch[^>]*?fragment="([a-z]+)"[^>]*\/>/g, (_m, p) => htmlToText(fragments[`../fragments/${p}.html`] ?? ''))
    .replace(/<ArchFigure[^>]*\/>/g, '')
    // the "at a glance" block: three plain lines (the attributes are JSON strings)
    .replace(/<Summary\s+what=\{("(?:[^"\\]|\\.)*")\}\s+when=\{("(?:[^"\\]|\\.)*")\}\s+write=\{("(?:[^"\\]|\\.)*")\}[^>]*\/>/g,
      (_m, a, b, c) => `- **What:** ${JSON.parse(a)}\n- **When you need it:** ${JSON.parse(b)}\n- **You write:** ${JSON.parse(c)}`)
    .replace(/<BenchSpeed\s*\/>/g, () => speedMarkdown())   // data-driven sections: the same numbers as the page
    // a recipe's own files, as on the page; stashed, so the component rules below never touch the code
    .replace(/<RecipeFiles\s+name="([^"]+)"\s*\/>/g, (_m, n) => `\u0000${stash.push(recipeFilesMarkdown(n)) - 1}\u0000`)
    .replace(/<RecipeResult\s+name="([^"]+)"\s*\/>/g, (_m, n) => recipeResultMarkdown(n))
    .replace(/<Disclosure\s+summary="([^"]+)"[^>]*>/g, '\n**$1**\n')   // collapsed on the page, open in the export
    // an included example file: the file itself, as a code block
    .replace(/<Code\s+code=\{(\w+)\}(?:\s+lang="([^"]*)")?(?:\s+title="([^"]*)")?[^>]*\/>/g,
      (_m, name, lang, title) => raw[name] !== undefined ? `\`\`\`${lang ?? ''}${title ? ` title="${title}"` : ''}\n${raw[name].trimEnd()}\n\`\`\`` : '')
    .replace(/<LinkCard\s+title="([^"]+)"(?:\s+description="([^"]*)")?\s+href="([^"]+)"\s*\/>/g, (_m, t, d, h) => `- [${t}](${h})${d ? `: ${d}` : ''}`)
    // tiles and figures: their words, as a list (attributes in quotes; a value from an expression is left out)
    .replace(/<Entry\b[^>]*\/>/g, (tag) => {
      const t = attr(tag, 'title'), x = attr(tag, 'text'), h = attr(tag, 'href')
      return typeof t === 'string' ? `- ${typeof h === 'string' ? `[${t}](${h})` : t}${typeof x === 'string' ? `: ${x}` : ''}` : ''
    })
    .replace(/<Metric\b[^>]*\/>/g, (tag) => {
      const v = attr(tag, 'value'), l = attr(tag, 'label'), d = attr(tag, 'detail')
      return typeof v === 'string' && typeof l === 'string' ? `- **${v}** ${l}${typeof d === 'string' ? ` (${d})` : ''}` : ''
    })
    .replace(/<Badge\b[^>]*>([^<]*)<\/Badge>/g, '$1')
    .replace(/`[^`\n]+`/g, (code) => `\u0000${stash.push(code) - 1}\u0000`)   // inline code is text: keep `<AguiChat />` in it
    .replace(/<[A-Z][A-Za-z]*(\s[^>]*)?\/>/g, '')   // any other self-closing component (live widgets)
    .replace(/<Card\s+title="([^"]+)"[^>]*>/g, '**$1.** ')
    .replace(/<TabItem\s+label="([^"]+)"[^>]*>/g, '\n**$1**\n')
    .replace(/<\/?(CardGrid|Card|Tabs|TabItem|Steps|Aside|LiveDemo|Stats|Fragment|Disclosure|details|summary)[^>]*>/g, '')
    .replace(/<\/?[A-Z][A-Za-z]*(\s[^>]*)?>/g, '')   // any other wrapper (Entries, Metrics, Specimen): its content stays
    .replace(/\u0000(\d+)\u0000/g, (_m, i) => stash[Number(i)])
}

/** MDX -> Markdown: components become their Markdown equivalents, code blocks stay exactly as written. */
function mdxToMd(body: string): string {
  const raw: Record<string, string> = {}
  for (const [, name, path] of body.matchAll(/^import\s+(\w+)\s+from\s+'([^']+)\?raw';?\s*$/gm)) {
    const file = path.split('/').pop()!
    const hit = Object.entries(examples).find(([k]) => k.endsWith(`/${file}`))
    if (hit) raw[name] = hit[1]
  }
  const text = body.replace(/^(?:\s*import .*\n)+/, '')   // the MDX imports at the top only; imports inside code blocks stay
  // split at fenced code blocks (``` or ~~~, indented too): only the prose between them is converted
  const parts = text.split(/(^[ \t]*(?:```|~~~)[^\n]*\n[\s\S]*?^[ \t]*(?:```|~~~)[ \t]*$)/m)
  return parts.map((p, i) => (i % 2 ? p : proseToMd(p, raw))).join('')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function entryMarkdown(e: CollectionEntry<'docs'>): string {
  const body = e.filePath?.endsWith('.mdx') ? mdxToMd(e.body ?? '') : (e.body ?? '').trim();
  return `# ${e.data.title}\n\n${e.data.description ? `> ${e.data.description}\n\n` : ''}${body}\n`;
}

export const pageUrl = (id: string, base: string) => `${base.replace(/\/$/, '')}/${id === 'index' ? '' : `${id}/`}`;

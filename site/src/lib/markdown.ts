/** A docs entry as plain Markdown for llms.txt, llms-full.txt and <page>.md (what AI tools read). */
import { speedMarkdown } from './bench';
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

/** MDX components -> Markdown equivalents (cards become links, tabs become labelled blocks). */
function mdxToMd(body: string): string {
  return body
    .replace(/^(?:\s*import .*\n)+/, '')   // the MDX imports at the top only; imports inside code blocks stay
    .replace(/<Arch[^>]*?fragment="([a-z]+)"[^>]*\/>/g, (_m, p) => htmlToText(fragments[`../fragments/${p}.html`] ?? ''))
    .replace(/<ArchFigure[^>]*\/>/g, '')
    // the "at a glance" block: three plain lines (the attributes are JSON strings)
    .replace(/<Summary\s+what=\{("(?:[^"\\]|\\.)*")\}\s+when=\{("(?:[^"\\]|\\.)*")\}\s+write=\{("(?:[^"\\]|\\.)*")\}[^>]*\/>/g,
      (_m, a, b, c) => `- **What:** ${JSON.parse(a)}\n- **When you need it:** ${JSON.parse(b)}\n- **You write:** ${JSON.parse(c)}`)
    .replace(/<BenchSpeed\s*\/>/g, () => speedMarkdown())   // data-driven sections: the same numbers as the page
    .replace(/<[A-Z][A-Za-z]*(\s[^>]*)?\/>/g, '')   // any other self-closing component (live widgets)
    .replace(/<LinkCard\s+title="([^"]+)"(?:\s+description="([^"]*)")?\s+href="([^"]+)"\s*\/>/g, (_m, t, d, h) => `- [${t}](${h})${d ? `: ${d}` : ''}`)
    .replace(/<Card\s+title="([^"]+)"[^>]*>/g, '**$1.** ')
    .replace(/<TabItem\s+label="([^"]+)"[^>]*>/g, '\n**$1**\n')
    .replace(/<\/?(CardGrid|Card|Tabs|TabItem|Steps|Aside|LiveDemo|Stats|Fragment|details|summary)[^>]*>/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function entryMarkdown(e: CollectionEntry<'docs'>): string {
  const body = e.filePath?.endsWith('.mdx') ? mdxToMd(e.body ?? '') : (e.body ?? '').trim();
  return `# ${e.data.title}\n\n${e.data.description ? `> ${e.data.description}\n\n` : ''}${body}\n`;
}

export const pageUrl = (id: string, base: string) => `${base.replace(/\/$/, '')}/${id === 'index' ? '' : `${id}/`}`;

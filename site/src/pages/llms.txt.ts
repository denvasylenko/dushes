import { getCollection } from 'astro:content';
import type { APIRoute } from 'astro';
import { pageUrl } from '../lib/markdown';

/** /llms.txt: what the site is and every page with its one-line summary (https://llmstxt.org). */
export const GET: APIRoute = async ({ site }) => {
  const base = new URL(import.meta.env.BASE_URL.replace(/\/?$/, '/'), site).href;
  const ORDER = ['start', 'getting-started', 'backend', 'frontend', 'form', 'concepts', 'reference', 'specifications'];
  const docs = (await getCollection('docs')).sort((a, b) => a.id.localeCompare(b.id));
  const group = (id: string) => (id.includes('/') ? id.split('/')[0] : 'start');
  const groups = new Map<string, string[]>();
  for (const d of docs) {
    const g = group(d.id);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(`- [${d.data.title}](${pageUrl(d.id, base).replace(/\/$/, '')}.md): ${d.data.description ?? ''}`);
  }
  const text = `# formguide\n\n> A chat agent that guides people through large forms: it shows where to click, answers from the business's documents, reads the user's documents and fills fields with their confirmation. Python backend (LangGraph, any LangChain model), AG-UI on the wire, a Web Component chat for the browser.\n\nAll pages in one file: ${base}llms-full.txt\n\n${[...groups].sort((a, b) => ORDER.indexOf(a[0]) - ORDER.indexOf(b[0])).map(([g, l]) => `## ${g}\n\n${l.join('\n')}`).join('\n\n')}\n`;
  return new Response(text, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};

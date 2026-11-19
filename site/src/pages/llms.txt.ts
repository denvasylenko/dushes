import { getCollection } from 'astro:content';
import type { APIRoute } from 'astro';
import { pageUrl } from '../lib/markdown';

/** /llms.txt: what the site is and every page with its one-line summary (https://llmstxt.org). */
export const GET: APIRoute = async ({ site }) => {
  const base = new URL(import.meta.env.BASE_URL.replace(/\/?$/, '/'), site).href;
  const ORDER = ['start', 'get-started', 'frontend', 'agents', 'reference'];
  const docs = (await getCollection('docs')).sort((a, b) => a.id.localeCompare(b.id));
  const group = (id: string) => (id.includes('/') ? id.split('/')[0] : 'start');
  const groups = new Map<string, string[]>();
  for (const d of docs) {
    const g = group(d.id);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(`- [${d.data.title}](${pageUrl(d.id, base).replace(/\/$/, '')}.md): ${d.data.description ?? ''}`);
  }
  const text = `# Dushes\n\n> Dushes is an AI assistant for your whole site or app. It answers from your pages and documents, takes people to the right page, tab or section, and when a page holds a form, its UI agent fills the form with them after they confirm. Start with the site agent (Dushes) and its site map; the UI agent (the class FormGuide) works on each form page, and the researcher gives deep answers from your documents. Before launch, describe your site by the guide: ${base}get-started/describe-your-site.md. Python backend (LangGraph, any LangChain model; the package is \`formguide\`), AG-UI on the wire, the <agui-chat> Web Component in the browser.\n\nAll pages in one file: ${base}llms-full.txt\n\n${[...groups].sort((a, b) => ORDER.indexOf(a[0]) - ORDER.indexOf(b[0])).map(([g, l]) => `## ${g}\n\n${l.join('\n')}`).join('\n\n')}\n`;
  return new Response(text, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};

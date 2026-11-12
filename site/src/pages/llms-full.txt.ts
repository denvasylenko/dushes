import { getCollection } from 'astro:content';
import type { APIRoute } from 'astro';
import { entryMarkdown, pageUrl } from '../lib/markdown';

/** /llms-full.txt: every page as Markdown, each headed by its address. Also the docs assistant's corpus. */
export const GET: APIRoute = async ({ site }) => {
  const base = new URL(import.meta.env.BASE_URL.replace(/\/?$/, '/'), site).href;
  const docs = (await getCollection('docs')).sort((a, b) => a.id.localeCompare(b.id));
  const text = docs.map((d) => `<!-- page: ${pageUrl(d.id, base)} -->\n${entryMarkdown(d)}`).join('\n\n---\n\n');
  return new Response(text, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};

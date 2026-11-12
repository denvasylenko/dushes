import { getCollection, type CollectionEntry } from 'astro:content';
import type { APIRoute, GetStaticPaths } from 'astro';
import { entryMarkdown } from '../lib/markdown';

/** /<page>.md: one page as Markdown, for "Copy page" and AI tools. */
export const getStaticPaths = (async () =>
  (await getCollection('docs')).map((entry) => ({ params: { slug: entry.id }, props: { entry } }))) satisfies GetStaticPaths;

export const GET: APIRoute = ({ props }) =>
  new Response(entryMarkdown((props as { entry: CollectionEntry<'docs'> }).entry), { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } });

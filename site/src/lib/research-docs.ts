/**
 * The researcher's test documents, for the pages that show them in full (/research-documents/<set>/<name>/).
 * The list and every figure come from research-demo.json (QA's `research_depth.py --demo`); the text is read at
 * build time from backend/demo/research_corpora/<set>/, the same files the researcher is asked about. Each set has
 * one instruction to AI assistants planted in a document on purpose: the page prints it as text and marks it.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { Marked } from 'marked'
import DEMO from '../data/research-demo.json'

export interface Doc { id: string; title: string; pages?: number; words?: number; bytes?: number; format?: string; about?: string }
export interface Planted { document: string; line: number; text: string }
export interface DocSet { id: string; name: string; about?: string; documents: Doc[]; planted?: Planted[] }

export const SETS = (DEMO as unknown as { sets: DocSet[] }).sets
const ROOT = join(process.cwd(), '..', 'backend', 'demo', 'research_corpora')   // the build runs in site/

export const isPdf = (d: Doc) => (d.format ?? '').toLowerCase() === 'pdf' || d.id.toLowerCase().endsWith('.pdf')
/** The document's address under /research-documents/<set>/: a page for Markdown, the file itself for a PDF.
 *  The docs host builds the same addresses for a source's "Open document" link (backend/docs_ai, RESEARCH_DOCS_URL):
 *  /research-documents/<set id>/<file name without .md>/#:~:text=<heading> and <file>.pdf#page=<n>. So the path, this
 *  slug and the headings' text (printed as in the file) are a contract: tell the Tech Lead before changing any. */
export const slug = (d: Doc) => d.id.replace(/\.md$/i, '')
export const href = (base: string, set: DocSet, d: Doc) => `${base}research-documents/${set.id}/${isPdf(d) ? d.id : `${slug(d)}/`}`
export const read = (set: string, id: string) => readFileSync(join(ROOT, set, id))
export const plantedIn = (set: DocSet, d: Doc) => (set.planted ?? []).filter((p) => p.document === d.id)
export const size = (d: Doc) => [d.pages ? `${d.pages} ${d.pages === 1 ? 'page' : 'pages'}` : '', d.words ? `${d.words.toLocaleString('en-US')} words` : '', isPdf(d) ? 'PDF' : '']
  .filter(Boolean).join(' · ')

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
/** The document as HTML. Raw HTML in it is printed, never run, so a hidden comment is visible; a planted line is
 *  found by its text (line numbers move when a generator changes) and marked. */
export function render(text: string, planted: Planted[]): string {
  const marks = planted.map((p) => p.text.trim()).filter(Boolean)
  const md = new Marked({
    gfm: true,
    renderer: {
      html({ text: raw }: { text: string }) {
        const t = raw.trim()
        return marks.includes(t)
          ? `<p class="rdoc-planted"><span>Planted for the benchmark, hidden in an HTML comment:</span> <code>${esc(t)}</code></p>`
          : esc(raw)
      },
    },
  })
  return md.parse(text, { async: false }) as string
}

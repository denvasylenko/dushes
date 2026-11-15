import type { APIRoute, GetStaticPaths } from 'astro'
import { SETS, isPdf, read } from '../../../lib/research-docs'

/** /research-documents/<set>/<name>.pdf: a set's PDF as it is in the repository. */
export const getStaticPaths = (() =>
  SETS.flatMap((set) => set.documents.filter(isPdf).map((d) => ({ params: { set: set.id, file: d.id.replace(/\.pdf$/i, '') } })))) satisfies GetStaticPaths

export const GET: APIRoute = ({ params }) =>
  new Response(new Uint8Array(read(params.set!, `${params.file}.pdf`)), { headers: { 'Content-Type': 'application/pdf' } })

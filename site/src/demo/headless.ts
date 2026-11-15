/**
 * Filling a form with no UI: one call to POST /prefill. A service sends the form's state and what it knows in plain
 * words ({state, text}); the answer is the values for this form's fields, each checked against the form
 * ({values, errors, notes}). No chat, no thread, nobody to tap a card. The recorded answers stand in when the hosted
 * agent is not there or has reached the demo's limit.
 */
import { schemaForm } from '../../../packages/agui-chat/src/formguide/schema'
import { SCHEMA } from './form'
import { FIELDS, LABEL, SAMPLES, display, type Sample } from './headless-data'
import { visitor } from './live'

export { FIELDS, SAMPLES, display, type Sample } from './headless-data'

// the page's static copy of the fields must be the form's own
const own = SCHEMA.sections.flatMap((x) => x.fields.map((f) => `${f.name}:${f.label ?? f.name}:${!!f.required}`)).join('|')
if (own !== FIELDS.map((f) => `${f.name}:${f.label}:${f.required}`).join('|')) console.error('headless-data.ts: FIELDS differ from the form schema')

export interface PrefillValue { name: string; label: string; value: unknown; display?: string; status?: string; source?: string; confidence?: string; evidence?: string }
export interface PrefillResult { values: PrefillValue[]; errors: string[]; notes: string[] }

/** The request body: the empty form's state and the text. `jsxHash` names the layout the host registered. */
export function prefillBody(text: string, jsxHash: string): { state: Record<string, unknown>; text: string } {
  const bridge = schemaForm(SCHEMA, { getValues: () => ({}), setValue: () => { /* the demo's form stays empty */ } })
  return { state: { config: bridge.config(), jsx_hash: jsxHash, form_id: SCHEMA.id }, text }
}

/** POST <agent>/prefill. Throws on anything but a 200 with the expected shape; the caller falls back. */
export async function prefillLive(prefillUrl: string, body: unknown, signal: AbortSignal): Promise<PrefillResult> {
  const id = visitor()
  const res = await fetch(prefillUrl, {
    method: 'POST', signal,
    headers: { 'Content-Type': 'application/json', ...(id ? { 'X-Demo-Visitor': id } : {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(res.status === 429 ? 'limit' : `HTTP ${res.status}`)
  const out = await res.json() as PrefillResult
  if (!Array.isArray(out?.values)) throw new Error('unexpected answer')
  return { values: out.values, errors: out.errors ?? [], notes: out.notes ?? [] }
}

/** The recorded answer for a sample: the shape the server sends, with nothing leaving the page. */
export async function prefillRecorded(sample: Sample): Promise<PrefillResult> {
  await new Promise((r) => setTimeout(r, 700))
  return {
    values: Object.entries(sample.values).map(([name, value]) => ({
      name, label: LABEL[name], value, display: display(value), status: 'now', source: 'text', confidence: 'high',
    })),
    errors: [],
    notes: [],
  }
}

import type { Config, UiState } from './types'

// ---------------------------------------------------------------- form backend (mock of the Java service)

/** Optional domain knowledge the form backend ships with the form (see backend/app/domain/packs.py). */
export type DomainPack = Record<string, unknown> | null

export async function javaForms(): Promise<string[]> {
  const r = await fetch('/java/forms')
  return r.json()
}

export async function javaForm(formId: string): Promise<{ form_id: string; jsx: string; config: Config; domain: DomainPack }> {
  const r = await fetch(`/java/form?form_id=${encodeURIComponent(formId)}`)
  return r.json()
}

export async function javaEvent(formId: string, state: Config['state'], changes: Record<string, unknown>): Promise<Config> {
  const r = await fetch('/java/event', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ form_id: formId, state, changes }),
  })
  return r.json()
}

// ---------------------------------------------------------------- agent

/** Sent once per form: the JSX and, if the form backend provides it, the domain pack. */
/** Register the form's JSX once. With the initial config the server also checks value formats. */
export async function registerLayout(jsx: string, formId: string, domain: DomainPack, config?: Config): Promise<string> {
  const r = await fetch('/agent/layouts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsx, form_id: formId, domain, config }),
  })
  const res = await r.json()
  for (const w of res.warnings ?? []) console.warn(`formguide: ${w}`)
  return res.jsx_hash
}

// ---------------------------------------------------------------- knowledge base (managers) and attachments

export type KbDoc = { doc_id: string; filename: string; bytes: number; chars: number }
export type KbCompiled = {
  summary?: string; rules?: string[]; flow_hints?: string[]; field_notes?: Record<string, string>
  dropped_fields?: string[]; compiled_at?: string
} | null

export async function kbGet(formId: string): Promise<{ documents: KbDoc[]; compiled: KbCompiled }> {
  const r = await fetch(`/agent/kb/${formId}`)
  return r.json()
}

export async function kbUpload(formId: string, files: FileList | File[]): Promise<void> {
  const body = new FormData()
  for (const f of Array.from(files)) body.append('files', f)
  const r = await fetch(`/agent/kb/${formId}/documents`, { method: 'POST', body })
  if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText)
}

export async function kbDelete(formId: string, docId: string): Promise<void> {
  await fetch(`/agent/kb/${formId}/documents/${docId}`, { method: 'DELETE' })
}

/** Compile the documents into the domain pack; needs the form (JSX + config) for field names and labels. */
export async function kbCompile(formId: string, jsx: string, config: Config): Promise<KbCompiled> {
  const r = await fetch(`/agent/kb/${formId}/compile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsx, config }),
  })
  if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText)
  return r.json()
}

export type Attachment = { id: string; filename: string }

/** The form as the agent gets it with every run (AG-UI `state`). */
export type FormState = { config: Config; jsx_hash: string; form_id: string; ui: UiState; attachments?: Attachment[] }

/** Frontend tools: declared to the agent with each run and executed here, in the browser. */
export const FRONTEND_TOOLS: { name: string; description: string; parameters: Record<string, unknown>; run: (args: Record<string, unknown>) => string }[] = [
  {
    name: 'get_user_locale',
    description: "The user's browser language, time zone and preferred date format. Call it when you need to " +
      'interpret or explain dates, times or numbers in the user\'s local conventions.',
    parameters: { type: 'object', properties: {} },
    run: () => JSON.stringify({
      language: navigator.language,
      time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      date_example: new Date(2026, 11, 31).toLocaleDateString(),
    }),
  },
]

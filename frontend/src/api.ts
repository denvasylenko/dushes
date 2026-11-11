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
export async function registerLayout(jsx: string, formId: string, domain: DomainPack): Promise<string> {
  const r = await fetch('/agent/layouts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsx, form_id: formId, domain }),
  })
  return (await r.json()).jsx_hash
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

export async function uploadAttachment(threadId: string, file: File): Promise<Attachment> {
  const body = new FormData()
  body.append('thread_id', threadId)
  body.append('file', file)
  const r = await fetch('/agent/attachments', { method: 'POST', body })
  if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText)
  return r.json()
}

export type AgentEvent = {
  type: string
  name?: string
  value?: any // eslint-disable-line @typescript-eslint/no-explicit-any
  messageId?: string
  delta?: string
  message?: string
}

export type RunInput = {
  threadId: string
  messages?: { role: 'user'; content: string }[]
  state: { config: Config; jsx_hash: string; form_id: string; ui: UiState; attachments?: Attachment[] }
  forwardedProps?: { command?: { resume: unknown } }
}

/** POST + SSE (events in the AG-UI format). */
export async function runAgent(input: RunInput, onEvent: (e: AgentEvent) => void): Promise<void> {
  const r = await fetch('/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ runId: crypto.randomUUID(), ...input }),
  })
  if (!r.ok || !r.body) {
    onEvent({ type: 'RUN_ERROR', message: `HTTP ${r.status}: ${await r.text()}` })
    return
  }
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += value
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, i)
      buf = buf.slice(i + 2)
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) onEvent(JSON.parse(line.slice(6)))
      }
    }
  }
}

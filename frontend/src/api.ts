import { HttpAgent, type Message, type Tool } from '@ag-ui/client'
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

// ---------------------------------------------------------------- conversation history

export type TranscriptEntry = {
  id: string
  ts: string
  kind: 'user' | 'assistant' | 'tool' | 'card' | 'question' | 'error' | 'notice'
  text?: string
  question?: string
  options?: { id: string; label: string }[]
  multiple?: boolean
  allow_text?: boolean
  field?: string
  answer?: { ids?: string[]; labels?: string[]; text?: string }
  names?: string[]
  files?: string[]
  name?: string
  input?: unknown
  changes?: unknown[]
  status?: 'pending' | 'accepted' | 'partial' | 'rejected' | 'dismissed' | 'answered'
}

/** The conversation as the user saw it (kept apart from the model's compacted history). */
export async function getThread(threadId: string): Promise<{ transcript: TranscriptEntry[]; pending_card: TranscriptEntry | null }> {
  const r = await fetch(`/agent/threads/${encodeURIComponent(threadId)}`)
  if (!r.ok) return { transcript: [], pending_card: null }
  return r.json()
}

export async function deleteThread(threadId: string): Promise<void> {
  await fetch(`/agent/threads/${encodeURIComponent(threadId)}`, { method: 'DELETE' })
}

export async function uploadAttachment(threadId: string, file: File): Promise<Attachment> {
  const body = new FormData()
  body.append('thread_id', threadId)
  body.append('file', file)
  const r = await fetch('/agent/attachments', { method: 'POST', body })
  if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText)
  return r.json()
}

// ---------------------------------------------------------------- agent runs over AG-UI (official client)

export type AgentEvent = {
  type: string
  name?: string
  value?: any // eslint-disable-line @typescript-eslint/no-explicit-any
  messageId?: string
  delta?: string
  message?: string
}

export type FormState = { config: Config; jsx_hash: string; form_id: string; ui: UiState; attachments?: Attachment[] }

/** One AG-UI agent per conversation; it keeps the message list the protocol sends with every run. */
export function makeAgent(threadId: string, initialMessages: Message[] = []): HttpAgent {
  return new HttpAgent({ url: '/agent/run', threadId, initialMessages })
}

/** Frontend tools: declared to the agent with every run, executed here in the browser. */
export const FRONTEND_TOOLS: (Tool & { run: (args: Record<string, unknown>) => string })[] = [
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

export type Turn = {
  state: FormState
  message?: string
  /** a field-change card: {accepted, config, ui?, names?}; a question card: {answer: {ids?, text?}} or {accepted: false} */
  resume?: { accepted?: boolean; config?: Config; ui?: UiState; names?: string[]; answer?: { ids?: string[]; text?: string } }
  prefill?: { data?: Record<string, unknown>; text?: string; attachment_ids?: string[]; language?: string }
}

/** One turn: run the agent, execute any frontend tools it calls, and continue until it is done. */
export async function runTurn(agent: HttpAgent, turn: Turn, onEvent: (e: AgentEvent) => void): Promise<void> {
  agent.setState(turn.state)
  if (turn.message) agent.addMessage({ id: crypto.randomUUID(), role: 'user', content: turn.message })
  let forwardedProps: Record<string, unknown> = {
    ...(turn.resume ? { command: { resume: turn.resume } } : {}),
    ...(turn.prefill ? { prefill: turn.prefill } : {}),
  }
  const tools = FRONTEND_TOOLS.map(({ name, description, parameters }) => ({ name, description, parameters }))
  for (let round = 0; round < 5; round++) {
    const calls: { id: string; name: string; args: Record<string, unknown> }[] = []
    let failed = false
    try {
      await agent.runAgent({ tools, forwardedProps }, {
        onEvent: ({ event }) => { onEvent(event as unknown as AgentEvent) },
        onRunErrorEvent: () => { failed = true },
        onToolCallEndEvent: ({ event, toolCallName, toolCallArgs }) => {
          onEvent({ type: 'TOOL_CALL_DONE', name: toolCallName, value: toolCallArgs })
          if (FRONTEND_TOOLS.some((t) => t.name === toolCallName)) calls.push({ id: event.toolCallId, name: toolCallName, args: toolCallArgs })
        },
      })
    } catch (e) {
      if (!failed) onEvent({ type: 'RUN_ERROR', message: String(e) })
      return
    }
    if (!calls.length) return
    for (const c of calls) {
      const tool = FRONTEND_TOOLS.find((t) => t.name === c.name)!
      let content: string
      try { content = tool.run(c.args) } catch (e) { content = `error: ${String(e)}` }
      agent.addMessage({ id: crypto.randomUUID(), role: 'tool', toolCallId: c.id, content })
    }
    forwardedProps = {}   // the continuation run carries only the tool results
  }
}

/** The conversation as AG-UI messages, to give a restored agent its message list. */
export async function getThreadMessages(threadId: string): Promise<Message[]> {
  const r = await fetch(`/agent/threads/${encodeURIComponent(threadId)}?format=agui`)
  if (!r.ok) return []
  return (await r.json()).messages
}

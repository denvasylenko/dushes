import { useCallback, useEffect, useRef, useState } from 'react'
import { javaForm, kbCompile, kbDelete, kbGet, kbUpload, type KbCompiled, type KbDoc } from './api'

/**
 * Manager view: business documents scoped to one form. Uploaded documents are
 * compiled into the form's domain pack (rules, field notes) and become
 * searchable by the agent's document researcher.
 */
export default function Manager({ formId }: { formId: string }) {
  const [docs, setDocs] = useState<KbDoc[]>([])
  const [compiled, setCompiled] = useState<KbCompiled>(null)
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string>('')
  const input = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    const r = await kbGet(formId)
    setDocs(r.documents)
    setCompiled(r.compiled)
  }, [formId])

  useEffect(() => {
    void load()
  }, [load])

  const compile = async () => {
    setStatus('Compiling the documents into the form’s knowledge…')
    setError('')
    try {
      const f = await javaForm(formId) // the compiler needs the form's fields and labels
      setCompiled(await kbCompile(formId, f.jsx, f.config))
      setStatus('')
    } catch (e) {
      setError(String(e))
      setStatus('')
    }
  }

  const upload = async (files: FileList | null) => {
    if (!files?.length) return
    setStatus(`Uploading ${files.length} file(s)…`)
    setError('')
    try {
      await kbUpload(formId, files)
      await load()
      await compile()
    } catch (e) {
      setError(String(e))
      setStatus('')
    } finally {
      if (input.current) input.current.value = ''
    }
  }

  const remove = async (doc: KbDoc) => {
    await kbDelete(formId, doc.doc_id)
    await load()
    await compile()
  }

  const notes = Object.entries(compiled?.field_notes ?? {})

  return (
    <div className="manager">
      <section className="panel">
        <div className="panel-head">
          <h2>Business documents · {formId}</h2>
          <div className="row">
            <input ref={input} type="file" multiple accept=".md,.txt,.pdf" hidden onChange={(e) => void upload(e.target.files)} />
            <button className="primary" disabled={!!status} onClick={() => input.current?.click()}>Upload documents</button>
            <button disabled={!!status || !docs.length} onClick={() => void compile()}>Recompile</button>
          </div>
        </div>
        <p className="muted">
          Visible only to the assistant of this form. Supported: .md, .txt, .pdf. After every change the documents are
          compiled into rules and field notes the assistant always has, and stay searchable for detailed questions.
        </p>
        {status && <p className="status">{status}</p>}
        {error && <p className="err">{error}</p>}
        {docs.length === 0 ? (
          <p className="muted">No documents yet.</p>
        ) : (
          <table className="docs">
            <thead><tr><th>File</th><th>Size</th><th>Text</th><th /></tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.doc_id}>
                  <td>{d.filename}</td>
                  <td>{(d.bytes / 1024).toFixed(1)} KB</td>
                  <td>{d.chars.toLocaleString('en')} chars</td>
                  <td><button className="link" disabled={!!status} onClick={() => void remove(d)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {compiled && compiled.summary && (
        <section className="panel">
          <div className="panel-head">
            <h2>What the assistant learned</h2>
            <span className="muted">{compiled.compiled_at}</span>
          </div>
          <p>{compiled.summary}</p>
          {!!compiled.rules?.length && (
            <>
              <h3>Rules ({compiled.rules.length})</h3>
              <ul>{compiled.rules.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </>
          )}
          {!!compiled.flow_hints?.length && (
            <>
              <h3>Filling order hints</h3>
              <ul>{compiled.flow_hints.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </>
          )}
          {!!notes.length && (
            <>
              <h3>Notes attached to fields ({notes.length})</h3>
              <table className="docs">
                <tbody>{notes.map(([f, n]) => <tr key={f}><td><code>{f}</code></td><td>{n}</td></tr>)}</tbody>
              </table>
            </>
          )}
          {!!compiled.dropped_fields?.length && (
            <p className="err">Ignored notes for unknown fields: {compiled.dropped_fields.join(', ')}</p>
          )}
        </section>
      )}
    </div>
  )
}

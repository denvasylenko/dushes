import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { capabilitiesFor, entryToInterrupt, formguide } from '@formguide/agui-chat/formguide'
import { AguiChat } from '@formguide/agui-chat/react'
import type { AguiChatElement } from '@formguide/agui-chat'
import { FormProvider, Render } from '../Form'
import type { UiDirective } from '../types'
import { useDemoForm } from './useDemoForm'

/** The demo site: a portal of two businesses (demo/site.yaml), one chat across every page.
 * The site assistant (/site/run) answers about the site and moves around it; on a page with a form
 * it hands the turn to the form agent, which the page serves through the usual formguide plugin. */
type Part = { id: string; title: string; text: string }
type SitePage = { path: string; title: string; description: string; form: string | null
  tabs: Part[]; accordions: Part[]; sections: Part[] }
type SiteMap = { title: string; pages: SitePage[] }
type SiteDirective = { type: 'navigate'; path: string; tab?: string; section?: string; form_id?: string; handoff?: 'done' }

// stable props: a new array on every render would reapply the chat's options and cut the answer being typed
const STARTERS = ['I want a car loan of 900 000 for 3 years', 'When is the bank open on Saturday?', 'Book me a haircut tomorrow at 3 pm']
const pathOf = () => decodeURIComponent(location.hash.replace(/^#/, '')) || '/'
const THREAD_KEY = 'site:thread'
function threadId(): string {
  try {
    const t = localStorage.getItem(THREAD_KEY) ?? crypto.randomUUID()
    localStorage.setItem(THREAD_KEY, t)
    return t
  } catch { return crypto.randomUUID() }
}

export default function Site() {
  const [map, setMap] = useState<SiteMap | null>(null)
  const [path, setPath] = useState(pathOf)
  const [tab, setTab] = useState<Record<string, string>>({})
  const [open, setOpen] = useState<string[]>([])
  const [ring, setRing] = useState<string | null>(null)
  const [thread] = useState(threadId)
  const chatRef = useRef<AguiChatElement | null>(null)
  const pendingHandoff = useRef<string | null>(null)   // a form the site assistant opened for the form agent

  useEffect(() => { fetch('/site/map').then((r) => r.json()).then(setMap) }, [])
  useEffect(() => {
    const on = () => setPath(pathOf())
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])

  const page = map?.pages.find((p) => p.path === path) ?? map?.pages[0] ?? null
  const demo = useDemoForm(page?.form ?? null)
  const pageRef = useRef(page); pageRef.current = page
  const demoRef = useRef(demo); demoRef.current = demo

  // the form agent's first run after a hand-off: once the form is on the page
  useEffect(() => {
    if (demo.form && pendingHandoff.current === demo.form.formId) {
      pendingHandoff.current = null
      void chatRef.current?.run({ forwardedProps: { handoff: true } })
    }
  }, [demo.form])

  const go = useCallback((d: SiteDirective) => {
    if (d.form_id && d.handoff !== 'done') pendingHandoff.current = d.form_id   // 'done': the form agent already answered in this run
    location.hash = d.path
    const target = d.tab ?? d.section
    if (d.tab) {
      setTab((t) => ({ ...t, [d.path]: d.tab! }))
      setOpen((o) => [...o.filter((x) => x !== d.tab), d.tab!])
    }
    if (target) {
      window.setTimeout(() => {
        document.getElementById(`part-${target}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        setRing(target)
        window.setTimeout(() => setRing(null), 2400)
      }, 80)
    } else {
      document.querySelector('.site-main')?.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [])

  // one chat for the whole site: the formguide plugin draws the form agent's cards; the run's state
  // carries the page and, on a form page, the form
  const plugins = useMemo(() => {
    const fg = formguide({
      getState: async () => (await demoRef.current.getState())!,
      applyChanges: (changes) => demoRef.current.applyChanges(changes),
      onDirective: (d) => demoRef.current.applyDirective(d as UiDirective),
      baseUrl: '/agent',
    })
    const formRun = fg.beforeRun!
    fg.beforeRun = async (input, chat) => {
      const p = pageRef.current
      const pageInfo = { path: p?.path ?? '/', title: p?.title ?? '' }
      if (demoRef.current.form) {
        await formRun(input, chat)
        input.state = { page: pageInfo, form: input.state }
      } else {
        input.state = { page: pageInfo }
        input.forwardedProps = { ...(input.forwardedProps ?? {}), capabilities: capabilitiesFor() }
      }
    }
    // after a reload: the whole site conversation, and the open card of the form on this page
    fg.restore = async (id) => {
      const m: SiteMap = await (await fetch('/site/map')).json()
      const form = m.pages.find((p) => p.path === pathOf())?.form
      const r = await fetch(`/site/threads/${encodeURIComponent(id)}${form ? `?form_id=${form}` : ''}`)
      if (!r.ok) return null
      const d = await r.json()
      return { messages: d.messages ?? [], interrupt: entryToInterrupt(d.pending_card) }
    }
    const onEvent = fg.onEvent!
    fg.onEvent = (ev, chat) => {
      if (ev.type === 'CUSTOM' && ev.name === 'site_directive') { go(ev.value as SiteDirective); return true }
      return onEvent(ev, chat)
    }
    return [fg]
  }, [go])

  if (!map || !page) return <div className="loading">Loading the site…</div>
  const activeTab = tab[page.path] ?? page.tabs[0]?.id

  return (
    <div className="page site">
      <nav className="site-nav" aria-label="Site">
        {import.meta.env.BASE_URL !== '/' && <a className="back-docs" href="/">{'\u2039'} Docs</a>}
        <a className="site-logo" href="#/">{map.title}</a>
        {map.pages.filter((p) => p.path !== '/').map((p) => (
          <a key={p.path} href={`#${p.path}`} className={p.path === page.path ? 'on' : ''}>{p.title}</a>
        ))}
      </nav>
      <div className="app">
        <main className="form-pane site-main">
          <header className="form-head">
            <h1>{page.title}</h1>
            <p className="muted">{page.description}</p>
          </header>
          {page.tabs.length > 0 && (
            <div className="tabs site-tabs">
              <div className="tab-bar" role="tablist">
                {page.tabs.map((t) => (
                  <button key={t.id} role="tab" aria-selected={t.id === activeTab} className={`tab ${t.id === activeTab ? 'active' : ''}`}
                    onClick={() => setTab((x) => ({ ...x, [page.path]: t.id }))}>{t.title}</button>
                ))}
              </div>
              {page.tabs.filter((t) => t.id === activeTab).map((t) => (
                <div key={t.id} id={`part-${t.id}`} className={`tab-body ${ring === t.id ? 'ring' : ''}`}><p>{t.text}</p></div>
              ))}
            </div>
          )}
          {page.accordions.map((a) => {
            const isOpen = open.includes(a.id)
            return (
              <div key={a.id} id={`part-${a.id}`} className={`acc ${ring === a.id ? 'ring' : ''}`}>
                <button className="acc-head" aria-expanded={isOpen}
                  onClick={() => setOpen((o) => (isOpen ? o.filter((x) => x !== a.id) : [...o, a.id]))}>
                  <span aria-hidden="true">{isOpen ? '▾' : '▸'}</span>{a.title}
                </button>
                {isOpen && <div className="site-acc-body"><p>{a.text}</p></div>}
              </div>
            )
          })}
          {page.sections.map((s) => (
            <section key={s.id} id={`part-${s.id}`} className={`site-section ${ring === s.id ? 'ring' : ''}`}>
              <h2>{s.title}</h2>
              <p>{s.text}</p>
            </section>
          ))}
          {page.form && (
            <div className="site-form">
              {demo.failed ? <p className="muted">The form could not be loaded. Reload the page to try again.</p>
                : !demo.form || !demo.ctx ? <p className="muted">Loading the form…</p>
                  : <FormProvider value={demo.ctx}><Render node={demo.form.tree} /></FormProvider>}
            </div>
          )}
        </main>
        <aside className="chat-pane">
          <AguiChat
            ref={chatRef}
            className="chat-widget"
            url="/site/run"
            mode="inline"
            threadId={thread}
            persistThread={false}
            title={`${map.title} assistant`}
            subtitle="Ask about any page, or say what you want to do"
            starters={STARTERS}
            plugins={plugins}
          />
        </aside>
      </div>
    </div>
  )
}

import { createContext, useContext, useEffect, useRef } from 'react'
import type { Config, JsxNode, Option, Props, UiState } from './types'
import { DateInput, NumberInput, Select } from './controls'

export type Highlight = { target: string; hint: string; ts: number; also?: string[] } | null

type Ctx = {
  config: Config
  ui: UiState
  highlight: Highlight
  setValue: (name: string, value: unknown, immediate: boolean) => void
  setTab: (tabs: string, tab: string) => void
  toggleAccordion: (name: string) => void
  setFocused: (name: string | null) => void
}

const FormCtx = createContext<Ctx>(null!)
export const FormProvider = FormCtx.Provider

const p = (c: Ctx, name: string): Props => c.config.props[name] ?? { name, visible: false }

/** Registry of atomic components: JSX tag -> React component. */
export function Render({ node, off = false }: { node: JsxNode; off?: boolean }) {
  const c = useContext(FormCtx)
  if (node.tag === '#text') return <p className="note">{node.text}</p>
  const props = p(c, node.name)
  if (props.visible === false) return null
  const dis = off || !!props.disabled // disabled state is inherited from containers
  switch (node.tag) {
    case 'Tabs':
      return <Tabs node={node} off={dis} />
    case 'Tab':
      return (
        <>
          {props.disabled && <p className="note locked">🔒 This section is not available yet: complete the previous steps.</p>}
          {node.children.map((ch) => <Render key={ch.name} node={ch} off={dis} />)}
        </>
      )
    case 'Accordion':
      return <Accordion node={node} props={props} off={dis} />
    default:
      return <Field node={node} props={{ ...props, disabled: dis }} />
  }
}

function Tabs({ node, off }: { node: JsxNode; off: boolean }) {
  const c = useContext(FormCtx)
  const tabs = node.children.filter((t) => p(c, t.name).visible !== false)
  const active = tabs.find((t) => t.name === c.ui.activeTabs[node.name]) ?? tabs[0]
  return (
    <div className={`tabs depth-${node.name === 'main' ? 0 : 1}`} data-name={node.name}>
      <div className="tab-bar" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.name}
            role="tab"
            data-name={t.name}
            aria-selected={t === active}
            className={`tab ${t === active ? 'active' : ''} ${p(c, t.name).disabled ? 'locked' : ''} ${c.highlight?.target === t.name ? 'pulse' : ''}`}
            onClick={() => c.setTab(node.name, t.name)}
            title={p(c, t.name).disabled ? 'Not available yet' : undefined}
          >
            {p(c, t.name).disabled && '🔒 '}{p(c, t.name).label ?? t.name}
          </button>
        ))}
      </div>
      <div className="tab-body">{active && <Render node={active} off={off} />}</div>
    </div>
  )
}

function Accordion({ node, props, off }: { node: JsxNode; props: Props; off: boolean }) {
  const c = useContext(FormCtx)
  const open = c.ui.openAccordions.includes(node.name)
  return (
    <section className={`acc ${open ? 'open' : ''} ${c.highlight?.target === node.name ? 'pulse' : ''}`} data-name={node.name}>
      <button className="acc-head" onClick={() => c.toggleAccordion(node.name)} aria-expanded={open}>
        <span className="chev">{open ? '▾' : '▸'}</span>
        {props.label ?? node.name}
      </button>
      {open && <div className="acc-body">{node.children.map((ch) => <Render key={ch.name} node={ch} off={off} />)}</div>}
    </section>
  )
}

function Field({ node, props }: { node: JsxNode; props: Props }) {
  const c = useContext(FormCtx)
  const ref = useRef<HTMLDivElement>(null)
  const value = c.config.state[node.name]
  const lit = c.highlight?.target === node.name
  const ringed = lit || !!c.highlight?.also?.includes(node.name)   // one of several fields shown together
  const off = !!props.disabled
  const ro = !!props.readonly

  useEffect(() => {
    if (lit) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [lit, c.highlight?.ts])

  const common = {
    id: node.name,
    disabled: off,
    readOnly: ro,
    onFocus: () => c.setFocused(node.name),
  }
  let input
  switch (node.tag) {
    case 'Dropdown': {
      const opts: Option[] = props.options ?? []
      const cur = value as Option | null
      const known = !cur || opts.some((o) => o.id === cur.id)
      input = (
        <Select
          {...common}
          disabled={off || ro}
          invalid={!!props.error}
          value={cur?.id ?? ''}
          onChange={(e) => {
            const o = opts.find((x) => x.id === e.target.value) ?? null
            c.setValue(node.name, o, true)
          }}
        >
          <option value="">{opts.length ? '— select —' : '— no options —'}</option>
          {!known && <option value={cur!.id}>{cur!.name} (not in the list)</option>}
          {opts.map((o) => (
            <option key={o.id} value={o.id}>{o.name}</option>
          ))}
        </Select>
      )
      break
    }
    case 'Checkbox':
      return (
        <div ref={ref} data-name={node.name} className={`field check ${ringed ? 'pulse' : ''} ${off ? 'off' : ''}`}>
          <label>
            <input type="checkbox" {...common} checked={value === true}
              onChange={(e) => c.setValue(node.name, e.target.checked, true)} />
            {props.label}{props.required && <b className="req">*</b>}
          </label>
          {props.error && <div className="err">{props.error}</div>}
          {lit && c.highlight!.hint && <div className="bubble">{c.highlight!.hint}</div>}
        </div>
      )
    case 'FileUpload': {
      const f = value as { name: string } | null
      input = (
        <div className="file ctl-file">
          <input type="file" {...common}
            onChange={(e) => c.setValue(node.name, e.target.files?.[0] ? { name: e.target.files[0].name } : null, true)} />
          <label htmlFor={node.name}>{f ? 'Replace file' : 'Choose a file'}</label>
          {f && <span className="muted">{f.name}</span>}
        </div>
      )
      break
    }
    case 'DatePicker':
      input = <DateInput id={node.name} value={value as string} disabled={off} readOnly={ro} invalid={!!props.error}
        min={(props as Record<string, unknown>).min as string | undefined} max={(props as Record<string, unknown>).max as string | undefined} onFocus={common.onFocus}
        onChange={(iso) => c.setValue(node.name, iso, true)} />
      break
    case 'NumberInput':
      input = <NumberInput {...common} placeholder={props.placeholder} invalid={!!props.error} value={value as string}
        onChange={(v) => c.setValue(node.name, v, false)} />
      break
    default:
      input = (
        <input
          type="text"
          inputMode={node.tag === 'NumberInput' ? 'decimal' : undefined}
          {...common}
          placeholder={props.placeholder}
          value={(value as string) ?? ''}
          onChange={(e) => c.setValue(node.name, e.target.value, false)}
        />
      )
  }
  return (
    <div ref={ref} data-name={node.name} className={`field ${ringed ? 'pulse' : ''} ${off ? 'off' : ''} ${ro ? 'ro' : ''} ${props.error ? 'has-err' : ''}`}>
      <label htmlFor={node.name}>
        {props.label ?? node.name}{props.required && <b className="req">*</b>}
      </label>
      {input}
      {props.error && <div className="err">{props.error}</div>}
      {lit && c.highlight!.hint && <div className="bubble">{c.highlight!.hint}</div>}
    </div>
  )
}

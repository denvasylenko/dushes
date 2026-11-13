/**
 * Apple-style form controls for the demo pages: no browser chrome (date popups, spin buttons, select arrows).
 * The calendar itself is the chat widget's (calendar() from the formguide entry), so the form and the chat
 * pick dates the same way. Styles: controls.css, driven by the --c-* variables each page maps to its own colours.
 */
import { useEffect, useRef, useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react'
import { calendar } from '@formguide/agui-chat/formguide'

const T: Record<string, string> = { prevMonth: 'Previous month', nextMonth: 'Next month', pickDate: 'Choose a date' }
const t = (k: string) => T[k] ?? k
const lang = () => document.documentElement.lang || navigator.language || 'en'

const fmt = (iso: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso
  return new Intl.DateTimeFormat(lang(), { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(`${iso}T00:00:00`))
}

/** A date field: shows the date in words; a tap opens the calendar in a popover under it. */
export function DateInput({ id, value, onChange, disabled, readOnly, min, max, invalid, onFocus }: {
  id?: string; value: string | null | undefined; onChange: (iso: string) => void; disabled?: boolean; readOnly?: boolean
  min?: string; max?: string; invalid?: boolean; onFocus?: () => void
}) {
  const [open, setOpen] = useState(false)
  const pop = useRef<HTMLDivElement>(null)
  const wrap = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open || !pop.current) return
    const el = calendar({ lang: lang(), value: value || null, limits: { min, max }, t, onPick: (iso) => { onChange(iso); setOpen(false) } })
    pop.current.replaceChildren(el)
    el.querySelector<HTMLElement>('.cal-d.on, .cal-d.today, .cal-d:not(:disabled)')?.focus()
    const away = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="ctl-date" ref={wrap}>
      <button type="button" id={id} className={`ctl-field ctl-face${invalid ? ' bad' : ''}`} disabled={disabled || readOnly}
        aria-haspopup="dialog" aria-expanded={open} onFocus={onFocus} onClick={() => setOpen((o) => !o)}>
        <span className={value ? '' : 'ph'}>{value ? fmt(value) : t('pickDate')}</span>
        <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <rect x="2.5" y="3.5" width="11" height="10" rx="2" /><path d="M2.5 6.5h11M5.5 2v3M10.5 2v3" />
        </svg>
      </button>
      {open && <div className="ctl-pop" role="dialog" ref={pop} />}
    </div>
  )
}

const chevron = (d: string) => (
  <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
)

/** A number field with the stepper joined to its right edge: two halves on the full height, chevrons. */
export function NumberInput({ value, onChange, step = 1, min, max, invalid, ...rest }: Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> & {
  value: string | number | null | undefined; onChange: (v: string) => void; step?: number; min?: number; max?: number; invalid?: boolean
}) {
  const nudge = (dir: 1 | -1) => {
    const n = Number(String(value ?? '').replace(/\s/g, '').replace(',', '.')) || 0
    let next = n + dir * step
    if (min !== undefined) next = Math.max(min, next)
    if (max !== undefined) next = Math.min(max, next)
    onChange(String(next))
  }
  return (
    <div className="ctl-num">
      <input {...rest} type="text" inputMode="decimal" className={`ctl-field${invalid ? ' bad' : ''}`} value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); nudge(e.key === 'ArrowUp' ? 1 : -1) } }} />
      {!rest.disabled && !rest.readOnly && (
        <div className="ctl-step">
          <button type="button" tabIndex={-1} aria-label="Increase" onClick={() => nudge(1)}>{chevron('M3 7.5 6 4.5l3 3')}</button>
          <button type="button" tabIndex={-1} aria-label="Decrease" onClick={() => nudge(-1)}>{chevron('M3 4.5 6 7.5l3-3')}</button>
        </div>
      )}
    </div>
  )
}

/** A select with its own chevron; the native arrow is hidden. */
export function Select({ invalid, children, className, ...rest }: SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean; children: ReactNode }) {
  return (
    <div className={`ctl-sel${className?.includes('small') ? ' small' : ''}`}>
      <select {...rest} className={`ctl-field${invalid ? ' bad' : ''}${className ? ` ${className}` : ''}`}>{children}</select>
    </div>
  )
}

export type Option = { id: string; name: string }

export type Props = {
  name: string
  label?: string
  visible?: boolean
  disabled?: boolean
  readonly?: boolean
  required?: boolean
  placeholder?: string
  options?: Option[]
  error?: string
}

export type Config = {
  props: Record<string, Props>
  state: Record<string, unknown>
}

export type JsxNode = {
  tag: string
  name: string
  children: JsxNode[]
  text?: string
}

/** What the frontend sends to the agent with every message. */
export type UiState = {
  activeTabs: Record<string, string>
  openAccordions: string[]
  focused: string | null
  /** User's local time, so the agent understands "tomorrow" / "next Tuesday". */
  now?: string
}

export type RevealStep = { type: 'tab'; tabs: string; tab: string } | { type: 'accordion'; name: string }

export type UiDirective = { type: 'focus'; target: string; reveal: RevealStep[]; hint: string }

/** A question card (on_interrupt with type "ask"). */
export type Question = {
  question: string
  options: { id: string; label: string }[]
  multiple: boolean
  allow_text: boolean
  field?: string
}

/** The user's answer to a question card, sent as resume {answer}. */
export type Answer = { ids?: string[]; labels?: string[]; text?: string }

export type ProposedChange = {
  name: string
  label: string
  value: unknown
  display: string
  reason: string
  reveal: RevealStep[]
}

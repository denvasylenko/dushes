/**
 * A scripted AG-UI agent for the live demo. It implements the widget's AgentLike (`run(input)` returning a
 * subscribable stream) and replays the events formguide's server sends: text, tool steps, "look here"
 * directives, cards, questions and quick replies. No server, no model: the script is picked by the
 * user's words or by the card being answered.
 */
import type { AguiEvent, RunAgentInput } from '../../../packages/agui-chat/src/types'
import type { DemoForm } from './form'
import { EMPLOYMENT, LOAN_TYPES, TERMS } from './form'

type Step = { wait?: number; ev: AguiEvent } | { wait?: number; text: string } | { wait?: number; tool: string; ms?: number }

const PROFILE = {
  full_name: 'Alex Morgan',
  email: 'alex.morgan@example.com',
  employment: EMPLOYMENT[0],
  monthly_income: 6200,
  loan_type: LOAN_TYPES[0],
  amount: 28000,
}
const LABELS: Record<string, string> = {
  full_name: 'Full name', email: 'Email', employment: 'Employment', monthly_income: 'Monthly income, $',
  loan_type: 'Loan type', amount: 'Amount, $', term: 'Term',
}
const SECTION: Record<string, string> = {
  full_name: 'applicant', email: 'applicant', employment: 'applicant', monthly_income: 'applicant',
  loan_type: 'loan', amount: 'loan', term: 'loan',
}
const REASONS: Record<string, string> = {
  full_name: 'From your profile', email: 'From your profile', employment: 'Your profile lists a current employer',
  monthly_income: 'Net salary from your last payslip', loan_type: 'You said you are buying a car', amount: 'The car price minus your $4,000 deposit',
}

export const STARTERS = ['Where do I enter my income?', 'Fill it in from my profile', 'Which loan suits me?']

let seq = 0
const id = (p: string) => `${p}-${Date.now().toString(36)}-${++seq}`
const show = (v: unknown): string => {
  if (v === null || v === undefined || v === '') return ''
  if (typeof v === 'number') return v.toLocaleString('en-US')
  if (typeof v === 'object' && 'name' in (v as object)) return String((v as { name: unknown }).name)
  return String(v)
}
/** The field's role, as the server sends it on every change (the widget formats values by it). */
const kindOf = (v: unknown): string => typeof v === 'number' ? 'number' : typeof v === 'boolean' ? 'bool'
  : v && typeof v === 'object' ? 'select' : typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) ? 'date' : 'text'
const reveal = (name: string) => [{ type: 'tab' as const, tabs: 'tabs', tab: SECTION[name] }]

export class ScriptedAgent {
  private lastCard: string | null = null
  constructor(private form: DemoForm) {}

  run(input: RunAgentInput) {
    const steps = this.script(input)
    let stopped = false
    const timers: ReturnType<typeof setTimeout>[] = []
    return {
      subscribe: (o: { next(e: AguiEvent): void; error(e: unknown): void; complete(): void }) => {
        const threadId = input.threadId
        const runId = id('run')
        const emit = (e: AguiEvent) => { if (!stopped) o.next(e) }
        void (async () => {
          const sleep = (ms: number) => new Promise<void>((r) => timers.push(setTimeout(r, ms)))
          emit({ type: 'RUN_STARTED', threadId, runId })
          await sleep(350)
          for (const s of steps) {
            if (stopped) return
            if (s.wait) await sleep(s.wait)
            if ('ev' in s) emit(s.ev)
            else if ('tool' in s) {
              const toolCallId = id('call')
              emit({ type: 'TOOL_CALL_START', toolCallId, toolCallName: s.tool })
              emit({ type: 'TOOL_CALL_END', toolCallId })
              await sleep(s.ms ?? 650)
              emit({ type: 'TOOL_CALL_RESULT', toolCallId, messageId: id('tool'), content: 'ok' })
            } else {
              const messageId = id('msg')
              emit({ type: 'TEXT_MESSAGE_START', messageId, role: 'assistant' })
              for (const chunk of s.text.match(/\S+\s*/g) ?? []) {
                emit({ type: 'TEXT_MESSAGE_CONTENT', messageId, delta: chunk })
                await sleep(18)
              }
              emit({ type: 'TEXT_MESSAGE_END', messageId })
            }
          }
          if (!stopped) { emit({ type: 'RUN_FINISHED', threadId, runId }); o.complete() }
        })()
        return { unsubscribe: () => { stopped = true; timers.forEach(clearTimeout) } }
      },
    }
  }

  private script(input: RunAgentInput): Step[] {
    const resume = (input.forwardedProps as { command?: { resume?: Record<string, unknown> } } | undefined)?.command?.resume
    if (resume) return this.answer(resume)
    const last = [...(input.messages ?? [])].reverse().find((m) => m.role === 'user')
    const text = String(last?.content ?? '').toLowerCase()
    if (/fill|profile|prefill|complete/.test(text)) return this.fill()
    if (/^why|why do/.test(text)) return this.why()
    if (/where|income|salary|find|show/.test(text)) return this.where()
    if (/loan|suit|which|best|recommend|rate/.test(text)) return this.advise()
    if (/term|month|payment/.test(text)) return this.term()
    return this.fallback()
  }

  private suggestions(items: string[], applies?: unknown[]): Step {
    return { ev: { type: 'CUSTOM', name: 'suggestions', value: { items, ...(applies ? { applies } : {}) } } }
  }

  private where(): Step[] {
    return [
      { tool: 'search_fields', ms: 550 },
      { tool: 'focus_field', ms: 300 },
      { ev: { type: 'CUSTOM', name: 'ui_directive', value: { type: 'focus', target: 'monthly_income', reveal: reveal('monthly_income'), hint: 'Net, after tax' } } },
      { text: 'It is **Monthly income** on the *Applicant* tab, highlighted now. Enter what you take home each month **after tax**, in dollars; bonuses only if they are regular.' },
      this.suggestions(['Fill it in from my profile', 'Why do you need my income?']),
    ]
  }

  private why(): Step[] {
    return [
      { tool: 'ask_documents', ms: 500 },
      { tool: 'docs.search_documents', ms: 600 },
      { text: 'The lender checks that the monthly payment stays **under 40% of your net income** (affordability rule, Lending policy 2.1). Your income sets the largest amount and term you can be offered; it is not shared outside the application.' },
      this.suggestions(['Fill it in from my profile', 'Which loan suits me?']),
    ]
  }

  private fill(): Step[] {
    const now = (this.form.state().config.state ?? {}) as Record<string, unknown>
    const changes = Object.entries(PROFILE).map(([name, value]) => ({
      name, label: LABELS[name], value, display: show(value), reason: REASONS[name], kind: kindOf(value),
      previous: now[name] ?? null, previous_display: show(now[name]) || null, reveal: reveal(name),
    })).filter((c) => JSON.stringify(c.previous) !== JSON.stringify(c.value))
    if (!changes.length) return [{ text: 'Everything from your profile is already in the form. Next is the **Term** on the *Loan* tab.' }, ...this.term()]
    this.lastCard = 'set_fields'
    return [
      { tool: 'get_outline', ms: 450 },
      { tool: 'get_fields', ms: 550 },
      { tool: 'propose_changes', ms: 350 },
      { text: `I found **${changes.length} values** in your profile. Check them and fill them in with one tap; untick anything you want to type yourself.` },
      { ev: { type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({ type: 'set_fields', card_id: id('card'), changes }) } },
    ]
  }

  private term(): Step[] {
    this.lastCard = 'ask'
    const now = (this.form.state().config.state ?? {}) as Record<string, unknown>
    return [{
      wait: 200,
      ev: {
        type: 'CUSTOM', name: 'on_interrupt', value: JSON.stringify({
          type: 'ask', card_id: id('ask'), question: 'Which **term** works for you?', field: 'term', label: 'Term', applies: true, reveal: reveal('term'),
          previous: now.term ?? null,
          options: TERMS.slice(1, 5).map((t) => ({ id: t.id, label: t.name, value: t })), allow_text: false,
        }),
      },
    }]
  }

  private advise(): Step[] {
    return [
      { tool: 'ask_documents', ms: 500 },
      { tool: 'docs.search_documents', ms: 700 },
      { tool: 'docs.read_section', ms: 600 },
      { text: 'For a car, the **Car loan** is cheaper than a personal loan: from **6.9% APR** with the car as security, up to $60,000 and 60 months. A personal loan starts at 9.4% but needs no security.\n\n*Source: Lending policy, section 3.2 "Secured loans".*' },
      this.suggestions(['Set the loan type to Car loan', 'Fill it in from my profile'], [
        [{ name: 'loan_type', label: 'Loan type', value: LOAN_TYPES[0], previous: this.form.state().config.state?.loan_type ?? null }],
        null,
      ]),
    ]
  }

  private answer(resume: Record<string, unknown>): Step[] {
    const card = this.lastCard
    this.lastCard = null
    if (resume.accepted === false) return [{ text: 'No problem, nothing changed. Tell me when you want to continue, or type the values yourself.' }]
    if (card === 'set_fields') {
      return [
        { text: 'Done. One choice left on the *Loan* tab: with your income, **36 months** keeps the payment under 15% of what you take home.' },
        ...this.term(),
      ]
    }
    const ids = (resume.answer as { ids?: string[] } | undefined)?.ids ?? []
    const months = Number(ids[0] ?? 36)
    const amount = Number(this.form.values().amount ?? 28000)
    const r = 0.069 / 12
    const pay = Math.round((amount * r) / (1 - (1 + r) ** -months))
    return [
      { text: `Set to **${months} months**. At 6.9% APR that is about **$${pay.toLocaleString('en-US')} a month** for $${amount.toLocaleString('en-US')}. The form is complete apart from the car make; submit it when you are ready.` },
      this.suggestions(['Which loan suits me?', 'Where do I enter my income?']),
    ]
  }

  private fallback(): Step[] {
    return [
      { text: 'This demo replays recorded turns, so it understands only a few requests. Try a suggestion below. The real agent answers anything about your form: [run it in three commands](get-started/quickstart/).' },
      this.suggestions(STARTERS),
    ]
  }
}

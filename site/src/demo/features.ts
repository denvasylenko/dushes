/**
 * "What the chat can do": one block per feature of <agui-chat>. A live block runs the shipped widget on the page with
 * a one-line scripted agent (nothing leaves the page); a card block replays a card gallery specimen; a link block
 * points at the place that shows it (the landing demo, the docs host). Every block links to its reference.
 */
import type { AguiEvent, RunAgentInput } from '../../../packages/agui-chat/src/types'

export type Live = { kind: 'live'; user: string; reply: string; /** replies to later messages, by their text */ more?: Record<string, string>; attrs?: Record<string, string>; options?: Record<string, unknown>; shadow?: boolean; upload?: boolean }
export type Card = { kind: 'card'; specimen: string }
export type Link = { kind: 'link'; href: string; label: string }
export interface Feature {
  id: string
  title: string
  why: string
  /** what to do to see it, for live blocks */
  try?: string
  /** screenshots of what cannot run on this page: feature ids in site/public/features/shots.json */
  shots?: string[]
  ref: { label: string; href: string }
  show: Live | Card | Link
  /** the browser code that turns it on or tunes it (frontend pages show browser code only) */
  code?: { lang: 'HTML' | 'JavaScript'; text: string }
}

const ANSWER = 'Your monthly income goes on the **Applicant** tab, in **Monthly income**. Enter what you take home after tax; include bonuses only if they are regular. If you are self-employed, use the average of the last 12 months.'
const LONG = Array.from({ length: 6 }, (_, i) => `${i + 1}. ${['Pick the loan type: car, personal or mortgage.', 'Enter the amount and the term.', 'Fill in your name and email.', 'Tell us how you are employed.', 'Add your monthly income after tax.', 'Attach a payslip or tax certificate, and send the form.'][i]}`).join('\n')

const TABLE = '| | Car loan | Personal loan |\n| --- | --- | --- |\n| Amount | up to $80,000 | up to $30,000 |\n| Term | 12 to 84 months | 6 to 60 months |\n| Rate from | 5.9% | 8.4% |'
const COMMANDS = [
  { id: 'summary', label: 'Summarise the form', hint: 'What is filled and what is missing', send: 'Summarise the form' },
  { id: 'person', label: 'Talk to a person', hint: 'Hand the conversation to the team', send: 'I want to talk to a person' },
]

export const FEATURES: Feature[] = [
  {
    id: 'layouts', title: 'Layouts: bubble, side panel, inline, page, hero',
    why: 'One tag, five places for the chat: a round launcher in the corner, a button with a side panel, a box in your page, the whole window, or only the message field until the first message. The side panel can also dock beside the page.',
    ref: { label: 'mode', href: '../../reference/agui-chat/' },
    show: { kind: 'link', href: '../playground/', label: 'Switch layouts in the playground' },
    code: { lang: 'HTML', text: '<!-- a round launcher that grows into a chat window -->\n<agui-chat mode="bubble"></agui-chat>\n\n<!-- the default: a button opens a side panel -->\n<agui-chat mode="floating"></agui-chat>\n\n<!-- fills the box you put it in -->\n<agui-chat mode="inline"></agui-chat>\n\n<!-- the whole window -->\n<agui-chat mode="page"></agui-chat>\n\n<!-- only the field, then the chat grows in place -->\n<agui-chat mode="hero"></agui-chat>\n\n<!-- the side panel docked: the page beside it stays usable -->\n<agui-chat mode="floating" modal="off"></agui-chat>' },
  },
  {
    id: 'menu', title: 'The + menu and commands',
    why: 'Everything that is not typing lives behind one +: files, your commands and your own menu items. Typing / in an empty field opens the commands too.',
    try: 'Tap + next to the message field and pick a command, or type / in the empty field. "Start over" is an item this page added: it clears the chat.',
    ref: { label: 'commands, menu', href: '../widget/#attachments' },
    show: { kind: 'live', user: 'What can I do here besides typing?', reply: 'Tap **+** next to the message field: you can add a file, run a command, or start over. Typing **/** in the empty field opens the commands as well.', upload: true,
      options: { commands: COMMANDS, menu: [{ id: 'restart', label: 'Start over', hint: 'Clear this chat' }] },
      more: { 'Summarise the form': 'Filled: **loan type** (car) and **amount** ($18,000). Still missing: **term**, **monthly income** and your **email**.', 'I want to talk to a person': 'I have passed this conversation to the team. Someone will write to you here within a working day.' } },
    code: { lang: 'JavaScript', text: "chat.options = {\n  commands: [   // the Commands row, and \"/\" in an empty field; `send` goes out as a message\n    { id: 'summary', label: 'Summarise the form', hint: 'What is filled and what is missing', send: 'Summarise the form' },\n    { id: 'person', label: 'Talk to a person', send: 'I want to talk to a person' },\n  ],\n  menu: [{ id: 'restart', label: 'Start over', hint: 'Clear this chat' }],   // your own items\n}\nchat.addEventListener('agui:menu-action', (e) => {\n  if (e.detail.id === 'restart') { e.preventDefault(); chat.reset() }   // handled here, nothing is sent\n})" },
  },
  {
    id: 'tables', title: 'Tables in an answer',
    why: 'A comparison reads best as a table. When the agent answers with a Markdown table, the chat draws it; a wide one scrolls sideways inside the answer.',
    ref: { label: 'Cards and answers', href: '../cards/' },
    show: { kind: 'live', user: 'Compare the car loan and the personal loan', reply: TABLE },
    code: { lang: 'HTML', text: '<agui-chat></agui-chat>   <!-- nothing to turn on: Markdown in an answer is drawn, tables included -->' },
  },
  {
    id: 'reply', title: 'Reply to a part of an answer',
    why: 'Ask about one sentence, not the whole answer. The quote goes with the question, so the answer is about exactly that.',
    try: 'Select a few words in the answer, tap Reply, then Add to chat. Do the same with another part and send: both quotes go in one message.',
    ref: { label: 'reply', href: '../widget/#reply-to-a-part-of-an-answer' },
    show: { kind: 'live', user: 'Where do I enter my income?', reply: ANSWER },
    code: { lang: 'HTML', text: "<agui-chat></agui-chat>              <!-- on by default -->\n<agui-chat reply=\"off\"></agui-chat>  <!-- without it -->" },
  },
  {
    id: 'fold', title: 'Long messages fold',
    why: 'A pasted document or a long list never pushes the conversation off the screen. One tap shows the rest.',
    try: 'Tap Show more under the answer.',
    ref: { label: 'collapseLines', href: '../widget/#long-messages-fold' },
    show: { kind: 'live', user: 'What are all the steps?', reply: LONG, attrs: { 'collapse-answers': 'on', 'collapse-lines': '4' } },
    code: { lang: 'HTML', text: "<agui-chat collapse-lines=\"8\" collapse-answers=\"on\"></agui-chat>   <!-- 0: never fold -->" },
  },
  {
    id: 'attach', title: 'Attachments',
    why: 'A payslip or a scan goes in the way it does in a messenger, and the cross takes it back before sending.',
    try: 'Tap the paper clip and pick any file. To remove it, hover it and click the cross. Nothing is uploaded from this page.',
    ref: { label: 'attach', href: '../widget/#attachments' },
    show: { kind: 'live', user: 'Can I send my payslip here?', reply: 'Yes: attach it with the paper clip and I will read the values from it.', upload: true },
    code: { lang: 'HTML', text: "<!-- the + button shows when files can be uploaded (the form plugin, or the upload option) -->\n<agui-chat attach-accept=\".pdf,.jpg\" attach-max-mb=\"20\"></agui-chat>" },
  },
  {
    id: 'shortcuts', title: 'Shortcut hints',
    why: 'Keyboard users learn the keys without a manual: ⌘ and ↵ on a Mac, Ctrl and Enter elsewhere, nothing on touch screens.',
    try: 'Hover the send, microphone or paper clip button for half a second.',
    ref: { label: 'shortcutHints', href: '../../reference/agui-chat/' },
    show: { kind: 'live', user: 'Hi!', reply: 'Hello. Hover the buttons in the message field below to see their keys.', upload: true },
    code: { lang: 'HTML', text: "<agui-chat></agui-chat>                       <!-- on by default -->\n<agui-chat shortcut-hints=\"off\"></agui-chat>  <!-- without them -->" },
  },
  {
    id: 'shadow', title: 'A composer that fits your page',
    why: 'The message field sits on your page as if it belonged there: soft, raised or flat.',
    ref: { label: 'composerShadow', href: '../../reference/agui-chat/' },
    show: { kind: 'live', user: 'Does it fit my design?', reply: 'Try the three shadows below and keep the one that suits your page.', shadow: true },
    code: { lang: 'HTML', text: "<agui-chat composer-shadow=\"raised\"></agui-chat>   <!-- soft (default), raised, none -->" },
  },
  {
    id: 'voice', title: 'Voice',
    why: 'A long answer is faster to say than to type. One microphone button, with the browser\'s recognition or your own server.',
    try: 'Tap the microphone and speak. It works where your browser supports speech recognition.',
    ref: { label: 'voice', href: '../../reference/agui-chat/' },
    show: { kind: 'live', user: 'Can I just talk to it?', reply: 'Yes. Tap the microphone and say what you need.' },
    code: { lang: 'HTML', text: "<agui-chat voice=\"server\"></agui-chat>   <!-- auto (default), browser, server, off -->\n<!-- server: your server transcribes (the transcription key) -->" },
    shots: ['server-voice'],
  },
  {
    id: 'finished', title: 'Finished cards, with Undo',
    why: 'Once accepted, a card shrinks to one calm line with Undo. The history stays readable, and the choice can be taken back.',
    try: 'Fill in the fields, then tap Undo.',
    ref: { label: 'Cards and answers', href: '../cards/' },
    show: { kind: 'card', specimen: 'set-fields' },
    code: { lang: 'JavaScript', text: "chat.use(formguide({\n  getState, applyChanges,\n  undoSeconds: 30,          // how long Undo stays on a finished card\n}))" },
  },
  {
    id: 'blocks', title: 'Cards from blocks',
    why: 'Your own cards, built from the same blocks as ours, look native without a line of frontend code.',
    try: 'Tap a button on the card.',
    ref: { label: 'Blocks', href: '../blocks/' },
    show: { kind: 'card', specimen: 'blocks-question' },
  },
  {
    id: 'suggestions', title: 'Suggested replies',
    why: 'The next step is one tap away, and a chip that fills fields shows what it will fill.',
    try: 'Tap a chip under the answer.',
    ref: { label: 'quickReplies', href: '../cards/' },
    show: { kind: 'card', specimen: 'suggestions' },
    code: { lang: 'HTML', text: "<agui-chat></agui-chat>                      <!-- starters and suggested replies, on by default -->\n<agui-chat quick-replies=\"off\"></agui-chat>  <!-- without them -->" },
  },
  {
    id: 'highlight', title: 'Changes light up in the form',
    why: 'When a card is accepted, the fields it filled flash in the form itself, so people see what changed and where.',
    ref: { label: 'The form plugin', href: '../widget/#the-form-plugin' },
    show: { kind: 'link', href: '../../#see-it-on-a-form', label: 'See it in the live demo' },
    code: { lang: 'JavaScript', text: "chat.use(formguide({\n  getState, applyChanges,\n  highlight: true,          // the default; false when your page draws its own\n}))" },
    shots: ['change-highlight'],
  },
  {
    id: 'limits', title: 'A public demo with limits',
    why: 'A public agent costs money. The demo counts messages per visitor and per day; past the limit, the chat says so and plays a recorded conversation.',
    ref: { label: 'A public demo host', href: '../../agents/shared/deploy/#a-public-demo-host' },
    show: { kind: 'link', href: '../../#see-it-on-a-form', label: 'Try the live demo' },
  },
]

const nid = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`

/** A one-reply agent: the first message gets the feature's reply; later ones a short line. */
export class OneReplyAgent {
  private runs = 0
  constructor(private reply: string, private more: Record<string, string> = {}) {}
  reset(): void { this.runs = 0 }
  run(input: RunAgentInput) {
    const last = [...(input.messages ?? [])].reverse().find((m) => m.role === 'user')
    const said = typeof last?.content === 'string' ? last.content.trim() : ''
    const text = this.runs++ === 0 ? this.reply : this.more[said] ?? 'This chat has one recorded reply. Tap **Replay** to start again.'
    const messageId = nid('m')
    const events: AguiEvent[] = [
      { type: 'RUN_STARTED', threadId: input.threadId, runId: nid('run') } as AguiEvent,
      { type: 'TEXT_MESSAGE_START', messageId, role: 'assistant' } as AguiEvent,
      { type: 'TEXT_MESSAGE_CONTENT', messageId, delta: text } as AguiEvent,
      { type: 'TEXT_MESSAGE_END', messageId } as AguiEvent,
      { type: 'RUN_FINISHED', threadId: input.threadId, runId: nid('run') } as AguiEvent,
    ]
    return {
      subscribe: (o: { next(e: AguiEvent): void; error(e: unknown): void; complete(): void }) => {
        let stopped = false
        void (async () => {
          for (const e of events) {
            if (stopped) return
            await new Promise((r) => setTimeout(r, 120))
            o.next(e)
          }
          o.complete()
        })()
        return { unsubscribe: () => { stopped = true } }
      },
    }
  }
}

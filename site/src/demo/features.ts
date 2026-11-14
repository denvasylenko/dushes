/**
 * "What the chat can do": one block per feature of <agui-chat>. A live block runs the shipped widget on the page with
 * a one-line scripted agent (nothing leaves the page); a card block replays a card gallery specimen; a link block
 * points at the place that shows it (the landing demo, the docs host). Every block links to its reference.
 */
import type { AguiEvent, RunAgentInput } from '../../../packages/agui-chat/src/types'

export type Live = { kind: 'live'; user: string; reply: string; attrs?: Record<string, string>; options?: Record<string, unknown>; shadow?: boolean; upload?: boolean }
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

export const FEATURES: Feature[] = [
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

/** Coming next: named only, no options until they ship. */
export const PLANNED = ['A "+" menu in the composer', 'Slash commands', 'Submit after review: the form is sent only when the user taps the card']

const nid = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`

/** A one-reply agent: the first message gets the feature's reply; later ones a short line. */
export class OneReplyAgent {
  private runs = 0
  constructor(private reply: string) {}
  reset(): void { this.runs = 0 }
  run(input: RunAgentInput) {
    const text = this.runs++ === 0 ? this.reply : 'This chat has one recorded reply. Tap **Replay** to start again.'
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

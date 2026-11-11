/**
 * The typewriter and the word fade-in, ported from the Cheese project's chat (Herefront AI, chat.js).
 *
 * Streamed text is revealed at an adaptive speed: at least `speed` characters a second, three times
 * the backlog when more is waiting, so the text never lags far behind the stream. A step finishes the
 * current word when it is short, never splits an emoji, and bold that is still being typed is already
 * bold. New words fade in from a slight blur; the text is redrawn every frame, so each word gets a
 * negative animation-delay (its age) and the fade simply continues instead of starting over.
 */

export interface TypewriterState {
  shown: number      // characters on screen
  acc: number        // fractional characters carried to the next frame
  last: number       // time of the previous frame
  marks: [number, number][]   // [text length on screen, time it appeared]
}

export const newState = (shown = 0): TypewriterState => ({ shown, acc: 0, last: 0, marks: [] })

/** Advance `st.shown` towards `text.length` for a frame at time `now` (ms). Pure, so it can be tested. */
export function step(st: TypewriterState, text: string, now: number, speed = 55): void {
  const target = text.length
  const dt = st.last ? Math.min(64, now - st.last) : 16
  st.last = now
  const back = target - st.shown
  if (back <= 0) return
  st.acc += (Math.max(speed, back * 3) * dt) / 1000
  const n = Math.floor(st.acc)
  if (!n) return
  st.acc -= n
  let to = Math.min(target, st.shown + n)
  const end = text.slice(to).search(/\s/)
  if (end >= 0 && end < 14) to += end          // the rest of a short word too
  else if (end < 0 && target - to < 14) to = target
  if (/[\ud800-\udbff]/.test(text.charAt(to - 1))) to++   // never half an emoji
  st.shown = Math.min(target, to)
}

/** The part of the text to show; an unfinished `**` is closed so bold is bold while typing. */
export function visible(text: string, shown: number): string {
  let s = text.slice(0, shown).replace(/\*$/, '')
  if ((s.match(/\*\*/g) || []).length % 2) s += '**'
  return s
}

/** Wrap the words of `box` that appeared less than `fadeMs` ago in fading spans (class `w`). */
export function fadeWords(box: HTMLElement, st: TypewriterState, now: number, fadeMs = 450): void {
  const len = box.textContent?.length ?? 0
  const marks = st.marks
  if (!marks.length || len > marks[marks.length - 1][0]) marks.push([len, now])
  while (marks.length > 1 && now - marks[1][1] >= fadeMs) marks.shift()
  const from = now - marks[0][1] >= fadeMs ? marks[0][0] : 0   // text before this is fully shown
  if (from >= len) return
  const walk = box.ownerDocument.createTreeWalker(box, 4 /* NodeFilter.SHOW_TEXT */)
  const nodes: Text[] = []
  let node: Node | null
  while ((node = walk.nextNode())) nodes.push(node as Text)
  let pos = 0
  for (const nd of nodes) {
    const s = nd.nodeValue ?? ''
    const start = pos
    pos += s.length
    if (pos <= from) continue
    const doc = box.ownerDocument
    const frag = doc.createDocumentFragment()
    const cut = Math.max(0, from - start)
    if (cut) frag.appendChild(doc.createTextNode(s.slice(0, cut)))
    s.slice(cut).replace(/\s*\S+\s*|\s+/g, (w, off: number) => {
      const at = start + cut + off
      let born = now
      for (const [l, t] of marks) if (l > at) { born = t; break }
      const sp = doc.createElement('span')
      sp.className = 'w'
      sp.textContent = w
      sp.style.animationDelay = `${-Math.round(now - born)}ms`
      frag.appendChild(sp)
      return w
    })
    nd.parentNode?.replaceChild(frag, nd)
  }
}

import { afterEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

// A screenshot pasted into the composer (or a file dropped on it) is attached like a file from the + button.

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
afterEach(() => { document.body.innerHTML = ''; vi.unstubAllGlobals() })

async function mount(upload?: (f: File) => Promise<unknown>): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  el.setAttribute('mode', 'inline'); el.setAttribute('persist-thread', 'off')
  document.body.appendChild(el)
  el.options = { url: '/agent/run', lang: 'en', ...(upload ? { upload: upload as never } : {}) }
  await tick()
  return el
}
const $ = (el: AguiChatElement, sel: string) => el.shadowRoot!.querySelector(sel) as HTMLElement

function paste(target: HTMLElement, files: File[]): Event {
  const e = new Event('paste', { bubbles: true, cancelable: true })
  Object.defineProperty(e, 'clipboardData', { value: { files } })
  target.dispatchEvent(e)
  return e
}

describe('pasting files', () => {
  it('a pasted screenshot becomes an attachment', async () => {
    const got: string[] = []
    const el = await mount(async (f) => { got.push(f.name); return { id: 'a1', filename: f.name } })
    const e = paste($(el, 'textarea'), [new File([new Uint8Array([1, 2, 3])], 'image.png', { type: 'text/plain' })])
    await tick(); await tick()
    expect(e.defaultPrevented).toBe(true)
    expect(got).toEqual(['image.png'])
    expect($(el, '.files').textContent).toContain('image.png')
  })

  it('pasted text stays text, and without uploads nothing is taken', async () => {
    const el = await mount()
    const e = paste($(el, 'textarea'), [new File(['x'], 'a.png')])
    expect(e.defaultPrevented).toBe(false)                        // no upload configured: the paste is left alone
    const plain = paste($(el, 'textarea'), [])
    expect(plain.defaultPrevented).toBe(false)
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '../src/index'
import type { AguiChatElement } from '../src/element'

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms))
async function mount(): Promise<AguiChatElement> {
  const el = document.createElement('agui-chat') as AguiChatElement
  for (const [k, v] of Object.entries({ mode: 'inline', typing: 'plain', lang: 'en', 'persist-thread': 'off' })) el.setAttribute(k, v)
  el.options = { upload: async (f: File) => ({ id: `att_${f.name}`, filename: f.name }) }
  document.body.appendChild(el)
  await tick()
  return el
}
const pick = async (el: AguiChatElement, files: File[]) => {
  const picker = el.shadowRoot!.querySelector('input[type=file]') as HTMLInputElement
  Object.defineProperty(picker, 'files', { value: files, configurable: true })
  picker.dispatchEvent(new Event('change'))
  await tick(20)
}

beforeEach(() => {
  document.body.innerHTML = ''
  vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 404 })))
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:preview' }))
})
afterEach(() => { vi.unstubAllGlobals() })

describe('attachments in the composer', () => {
  it('shows an image as a thumbnail and a document as a tile, inside the composer, each with a remove button', async () => {
    const el = await mount()
    await pick(el, [new File(['x'], 'photo.png', { type: 'image/png' }), new File(['%PDF'], 'passport scan.pdf', { type: 'application/pdf' })])
    const box = el.shadowRoot!.querySelector('.box')!
    const tiles = [...box.querySelectorAll('.files .att')] as HTMLElement[]
    expect(tiles).toHaveLength(2)                                              // inside the box, above the text
    expect(tiles[0].querySelector('img')!.getAttribute('src')).toBe('blob:preview')
    expect(tiles[1].classList.contains('doc')).toBe(true)
    expect(tiles[1].textContent).toContain('passport scan.pdf')
    expect(tiles[1].querySelector('.att-ext')!.textContent).toBe('PDF')
    ;(tiles[1].querySelector('.att-x') as HTMLButtonElement).click()
    expect(box.querySelectorAll('.files .att')).toHaveLength(1)
  })

  it('offers markup (the pencil) for an image still in the composer only', async () => {
    const el = await mount()
    await pick(el, [new File(['x'], 'photo.png', { type: 'image/png' })])
    ;(el.shadowRoot!.querySelector('.files .att-open') as HTMLButtonElement).click()
    expect(el.shadowRoot!.querySelector('dialog.zoom .zoom-edit')!.getAttribute('aria-label')).toBe('Mark up')
    ;(el.shadowRoot!.querySelector('dialog.zoom .zoom-x') as HTMLButtonElement).click()
    await tick()
    el.agent = { run: () => ({ subscribe: (o: { next: (e: unknown) => void; complete: () => void }) => { setTimeout(() => { o.next({ type: 'RUN_STARTED', threadId: 't', runId: 'r' }); o.next({ type: 'RUN_FINISHED', threadId: 't', runId: 'r' }); o.complete() }); return { unsubscribe() {} } } }) } as never
    await el.send('look')
    await tick(5)
    ;(el.shadowRoot!.querySelector('.msg.me .att-open') as HTMLButtonElement).click()   // a sent image: view only
    expect(el.shadowRoot!.querySelector('dialog.zoom')).not.toBeNull()
    expect(el.shadowRoot!.querySelector('dialog.zoom .zoom-edit')).toBeNull()
  })

  it('opens an image large, and closes it', async () => {
    const el = await mount()
    await pick(el, [new File(['x'], 'photo.png', { type: 'image/png' })])
    ;(el.shadowRoot!.querySelector('.att-open') as HTMLButtonElement).click()
    const zoom = el.shadowRoot!.querySelector('dialog.zoom') as HTMLDialogElement
    expect(zoom).not.toBeNull()
    expect(zoom.querySelector('img')!.getAttribute('src')).toBe('blob:preview')
    ;(zoom.querySelector('.zoom-x') as HTMLButtonElement).click()
    await tick()
    expect(el.shadowRoot!.querySelector('dialog.zoom')).toBeNull()
  })
})

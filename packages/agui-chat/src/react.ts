/** React wrapper: <AguiChat url="/agent/run" plugins={[formguide({...})]} onEvent={...} />. */
import { createElement, forwardRef, useEffect, useImperativeHandle, useRef, type ComponentType, type CSSProperties } from 'react'
import './index'
import { DEFAULTS, type AguiChatElement } from './element'
import type { AguiEvent, ChatOptions, FrontendTool, Plugin, Renderer } from './types'
import type { AgentLike } from './transport'

export interface AguiChatProps extends Partial<ChatOptions> {
  plugins?: Plugin[]
  tools?: FrontendTool[]
  renderers?: Record<string, Renderer>
  agent?: AgentLike
  onEvent?: (ev: AguiEvent) => void
  onRunStart?: () => void
  onRunEnd?: () => void
  onError?: (message: string) => void
  className?: string
  style?: CSSProperties
}

export const AguiChat = forwardRef<AguiChatElement | null, AguiChatProps>(function AguiChat(props, ref) {
  const el = useRef<AguiChatElement | null>(null)
  useImperativeHandle(ref, () => el.current as AguiChatElement)
  const { plugins, tools, renderers, agent, onEvent, onRunStart, onRunEnd, onError, className, style, ...rest } = props
  const options = Object.fromEntries(Object.entries(rest).filter(([k]) => k in DEFAULTS)) as Partial<ChatOptions>
  const key = JSON.stringify(options)

  useEffect(() => { if (el.current) el.current.options = options }, [key]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (el.current && plugins) el.current.plugins = plugins }, [plugins])
  useEffect(() => { for (const t of tools ?? []) el.current?.registerTool(t) }, [tools])
  useEffect(() => { for (const [k, r] of Object.entries(renderers ?? {})) el.current?.renderers.set(k, r) }, [renderers])
  useEffect(() => { if (el.current) el.current.agent = agent ?? null }, [agent])
  useEffect(() => {
    const node = el.current
    if (!node) return
    const on: [string, EventListener][] = [
      ['agui:event', (e) => onEvent?.((e as CustomEvent).detail)],
      ['agui:run-start', () => onRunStart?.()],
      ['agui:run-end', () => onRunEnd?.()],
      ['agui:error', (e) => onError?.((e as CustomEvent).detail)],
    ]
    on.forEach(([n, f]) => node.addEventListener(n, f))
    return () => on.forEach(([n, f]) => node.removeEventListener(n, f))
  }, [onEvent, onRunStart, onRunEnd, onError])

  return createElement('agui-chat', { ref: el, class: className, style })
})

/** What a React slot component receives: the slot's first argument as `data`, all of them as `args`, and the chat. */
export interface SlotProps<D = unknown> { data: D; args: unknown[]; chat: AguiChatElement }

type CreateRoot = (el: Element) => { render(node: unknown): void; unmount(): void }

/**
 * A React component as a slot of options.render:
 *   import { createRoot } from 'react-dom/client'
 *   <AguiChat render={{ assistant: reactSlot(createRoot, MyAnswer), empty: reactSlot(createRoot, Welcome) }} />
 * createRoot comes from your app, so this package does not depend on react-dom.
 */
export function reactSlot<D = unknown>(createRoot: CreateRoot, Component: ComponentType<SlotProps<D>>) {
  return (...args: unknown[]): HTMLElement => {
    const chat = args[args.length - 1] as AguiChatElement
    const el = document.createElement('div')
    el.className = 'react-slot'
    const root = createRoot(el)
    root.render(createElement(Component, { data: args[0] as D, args: args.slice(0, -1), chat }))
    return el
  }
}


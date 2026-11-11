/** React wrapper: <AguiChat url="/agent/run" plugins={[formguide({...})]} onEvent={...} />. */
import { createElement, forwardRef, useEffect, useImperativeHandle, useRef, type CSSProperties } from 'react'
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

/**
 * What every stand shares: the chat next to the form, and window.__stand for the tests, which read the form's Vue
 * state (never the DOM) and its errors: { values(), errors(), adapter, ready, error }.
 */
import { toRaw, watchEffect, type Ref } from 'vue'
import '@formguide/agui-chat'

declare const __ADAPTER__: string

export interface StandHooks { values: () => unknown; errors?: () => Record<string, string>; ready: Ref<boolean>; error: Ref<string | null> }

export function expose(name: string, h: StandHooks): void {
  const w = window as unknown as { __stand: Record<string, unknown> }
  w.__stand = { name, adapter: __ADAPTER__, values: () => JSON.parse(JSON.stringify(toRaw(h.values()))), errors: () => h.errors?.() ?? {},
                ready: false, error: null }
  watchEffect(() => { w.__stand.ready = h.ready.value; w.__stand.error = h.error.value })
}

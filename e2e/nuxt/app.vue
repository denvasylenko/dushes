<!-- The Nuxt (SSR) stand: the form is rendered on the server; the adapter registers the layout on mount. -->
<script setup lang="ts">
import { reactive, watchEffect } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'

declare const __ADAPTER__: string
const form = reactive({ name: '', email: '', guests: 1 })
const schema = { id: 'vue_nuxt', title: 'Sign-up', sections: [{ name: 'you', label: 'You', fields: [
  { name: 'name', label: 'Full name', required: true },
  { name: 'email', label: 'Email', required: true },
  { name: 'guests', label: 'Guests', type: 'number' as const },
] }] }
const { plugins, ready, error } = useFormguide(form, schema)
if (import.meta.client) {
  const w = window as unknown as { __stand: Record<string, unknown> }
  w.__stand = { name: 'nuxt', adapter: __ADAPTER__, values: () => JSON.parse(JSON.stringify(form)), errors: () => ({}), ready: false, error: null }
  watchEffect(() => { w.__stand.ready = ready.value; w.__stand.error = error.value })
}
</script>

<template>
  <main>
    <form id="ssr-form" @submit.prevent>
      <label data-name="name">Full name <input v-model="form.name" name="name" /></label>
      <label data-name="email">Email <input v-model="form.email" name="email" /></label>
      <label data-name="guests">Guests <input v-model.number="form.guests" name="guests" type="number" /></label>
    </form>
    <p v-if="error" class="adapter-error">{{ error }}</p>
    <ClientOnly><agui-chat mode="inline" url="/agent/run" typing="plain" persist-thread="off" lang="en" :plugins.prop="plugins" style="display:block;height:60vh"></agui-chat></ClientOnly>
  </main>
</template>

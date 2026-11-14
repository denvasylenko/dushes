<!-- Stand: a 3-step form with vue-router (hash history), one step per route. The state is one reactive object outside
     the router views (store.ts); "take me there" to a field of another step navigates there (onReveal returns
     router.push). "Re-render" remounts the step (a new key), "Hide" unmounts it (v-if): the values must survive. -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'
import { form, PLANS, STEPS } from './store'

const router = useRouter()
const renderKey = ref(0), shown = ref(true)

const schema = {
  id: 'vue_router', title: 'Membership', layout: 'tabs' as const,
  sections: [
    { name: 'personal', label: 'You', fields: [
      { name: 'name', label: 'Full name', required: true },
      { name: 'email', label: 'Email', required: true },
    ] },
    { name: 'address', label: 'Address', fields: [
      { name: 'street', label: 'Street' },
      { name: 'city', label: 'City' },
    ] },
    { name: 'extras', label: 'Plan', fields: [
      { name: 'plan', label: 'Plan', type: 'select' as const, options: PLANS },
      { name: 'start', label: 'Start date', type: 'date' as const, help: 'YYYY-MM-DD' },
      { name: 'notes', label: 'Notes', type: 'textarea' as const },
    ] },
  ],
}
const { plugins, ready, error } = useFormguide(form, schema, { onReveal: (section) => router.push({ name: section }).then(() => undefined) })
expose('router', { values: () => ({ ...form }), ready, error })
</script>

<template>
  <main class="page">
    <div class="form-col">
      <nav class="steps">
        <RouterLink v-for="s in STEPS" :key="s.name" :to="{ name: s.name }">{{ s.label }}</RouterLink>
        <button type="button" class="rerender" @click="renderKey++">Re-render</button>
        <button type="button" class="toggle" @click="shown = !shown">{{ shown ? 'Hide' : 'Show' }}</button>
      </nav>
      <form class="form" @submit.prevent>
        <RouterView v-slot="{ Component }"><component :is="Component" v-if="shown" :key="renderKey" /></RouterView>
      </form>
    </div>
    <p v-if="error" class="adapter-error">{{ error }}</p>
    <agui-chat mode="inline" url="/agent/run" typing="plain" persist-thread="off" lang="en" :plugins.prop="plugins"></agui-chat>
  </main>
</template>

<style>
body { margin: 0; font: 15px system-ui, sans-serif; }
.page { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; padding: 16px; }
@media (min-width: 900px) { .page { grid-template-columns: 1fr 420px; } }
.steps { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.steps .router-link-active { font-weight: 600; }
.step { display: grid; gap: 12px; border: 0; padding: 0; }
.step label { display: grid; gap: 4px; }
agui-chat { display: block; height: 70vh; }
</style>

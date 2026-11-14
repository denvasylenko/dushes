<!-- Stand 1: plain Vue state. v-model on reactive() and ref(), a watcher that clears the region when the country
     changes, regions computed from the country, and a computed total. -->
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const REGIONS: Record<string, string[]> = { de: ['Bavaria', 'Berlin', 'Hesse'], fr: ['Brittany', 'Normandy', 'Provence'], it: ['Lazio', 'Tuscany'] }
const form = reactive({ name: '', email: '', country: '', region: '', guests: 1, newsletter: false })
const note = ref('')
const regions = computed(() => REGIONS[form.country] ?? [])
const total = computed(() => form.guests * 25)
const watched = ref(0)   // how many times the watcher ran: the tests check that watchers fire
watch(() => form.country, () => { watched.value++; if (!regions.value.includes(form.region)) form.region = '' })

const schema = {
  id: 'vue_reactive', title: 'Event sign-up',
  sections: [{ name: 'you', label: 'You', fields: [
    { name: 'name', label: 'Full name', required: true },
    { name: 'email', label: 'Email', required: true },
    { name: 'country', label: 'Country', type: 'select' as const, options: [{ id: 'de', name: 'Germany' }, { id: 'fr', name: 'France' }, { id: 'it', name: 'Italy' }], required: true },
    { name: 'region', label: 'Region', type: 'select' as const, options: (v: Record<string, unknown>) => (REGIONS[String(v.country)] ?? []), visible: (v: Record<string, unknown>) => !!v.country },
    { name: 'guests', label: 'Guests', type: 'number' as const, help: '1 to 10' },
    { name: 'newsletter', label: 'Send me the newsletter', type: 'bool' as const },
  ] }],
}
const errors = () => (form.email && !/^\S+@\S+\.\S+$/.test(form.email) ? { email: 'Enter a valid email' } : {})
const { plugins, ready, error } = useFormguide(form, schema, { errors })
expose('reactive', { values: () => ({ ...form, note: note.value, total: total.value, watched: watched.value }), errors, ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label data-name="name">Full name <input v-model="form.name" name="name" /></label>
      <label data-name="email">Email <input v-model="form.email" name="email" type="email" /></label>
      <label data-name="country">Country
        <select v-model="form.country" name="country"><option value="">Choose</option><option value="de">Germany</option><option value="fr">France</option><option value="it">Italy</option></select>
      </label>
      <label v-if="form.country" data-name="region">Region
        <select v-model="form.region" name="region"><option value="">Choose</option><option v-for="r in regions" :key="r" :value="r">{{ r }}</option></select>
      </label>
      <label data-name="guests">Guests <input v-model.number="form.guests" name="guests" type="number" min="1" max="10" /></label>
      <label data-name="newsletter"><input v-model="form.newsletter" name="newsletter" type="checkbox" /> Send me the newsletter</label>
      <p class="total">Total: {{ total }} EUR</p>
    </form>
    <p v-if="error" class="adapter-error">{{ error }}</p>
    <agui-chat mode="inline" url="/agent/run" typing="plain" persist-thread="off" lang="en" :plugins.prop="plugins"></agui-chat>
  </main>
</template>

<style>
body { margin: 0; font: 15px system-ui, sans-serif; }
.page { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; padding: 16px; }
@media (min-width: 900px) { .page { grid-template-columns: 1fr 420px; } }
.form { display: grid; gap: 12px; }
.form label { display: grid; gap: 4px; }
agui-chat { display: block; height: 70vh; }
</style>

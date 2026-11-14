<!-- Stand: Vuetify 3. The library's own components bound to reactive state with v-model: v-select (single),
     v-select multiple with chips, v-date-input (labs in 3.7; its model is a Date, so a computed turns the state's ISO
     string into a Date and back), v-slider and v-autocomplete with static items, next to a v-text-field. data-name
     sits on each component's root (.v-input). -->
<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const COUNTRIES = [{ id: 'de', name: 'Germany' }, { id: 'fr', name: 'France' }, { id: 'it', name: 'Italy' }]
const LANGUAGES = [{ id: 'en', name: 'English' }, { id: 'de', name: 'German' }, { id: 'fr', name: 'French' }, { id: 'it', name: 'Italian' }]
const CITIES = [{ id: 'ber', name: 'Berlin' }, { id: 'par', name: 'Paris' }, { id: 'rom', name: 'Rome' }, { id: 'mun', name: 'Munich' }]
const form = reactive({ name: '', country: '', languages: [] as string[], start: '', budget: 20, city: '' })

const pad = (n: number) => String(n).padStart(2, '0')
const start = computed<Date | null>({   // the state keeps "YYYY-MM-DD" (local day, no time zone shift)
  get: () => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(form.start); return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null },
  set: (d) => { form.start = d ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` : '' },
})

const schema = {
  id: 'vue_vuetify', title: 'Trip request',
  sections: [{ name: 'trip', label: 'Trip', fields: [
    { name: 'name', label: 'Full name', required: true },
    { name: 'country', label: 'Country', type: 'select' as const, options: COUNTRIES, required: true },
    { name: 'languages', label: 'Languages', type: 'multiselect' as const, options: LANGUAGES },
    { name: 'start', label: 'Start date', type: 'date' as const, help: 'YYYY-MM-DD' },
    // a slider: FieldSchema has no min/max/step, so the range goes in help
    { name: 'budget', label: 'Budget (hundreds of EUR)', type: 'number' as const, help: '0 to 100, step 5' },
    { name: 'city', label: 'City', type: 'select' as const, options: CITIES },
  ] }],
}
const { plugins, ready, error } = useFormguide(form, schema)
expose('vuetify', { values: () => ({ ...form }), ready, error })
</script>

<template>
  <v-app>
    <main class="page">
      <form class="form" @submit.prevent>
        <v-text-field v-model="form.name" name="name" label="Full name" data-name="name" />
        <v-select v-model="form.country" :items="COUNTRIES" item-title="name" item-value="id" label="Country" data-name="country" />
        <v-select v-model="form.languages" :items="LANGUAGES" item-title="name" item-value="id" multiple chips label="Languages" data-name="languages" />
        <v-date-input v-model="start" label="Start date" data-name="start" />
        <v-slider v-model="form.budget" :min="0" :max="100" :step="5" thumb-label="always" label="Budget" data-name="budget" />
        <v-autocomplete v-model="form.city" :items="CITIES" item-title="name" item-value="id" label="City" data-name="city" />
      </form>
      <p v-if="error" class="adapter-error">{{ error }}</p>
      <agui-chat mode="inline" url="/agent/run" typing="plain" persist-thread="off" lang="en" :plugins.prop="plugins"></agui-chat>
    </main>
  </v-app>
</template>

<style>
body { margin: 0; font: 15px system-ui, sans-serif; }
.page { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; padding: 16px; }
@media (min-width: 900px) { .page { grid-template-columns: 1fr 420px; } }
.form { display: grid; gap: 12px; padding-top: 24px; }
agui-chat { display: block; height: 70vh; }
</style>

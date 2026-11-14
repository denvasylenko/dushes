<!-- Stand: PrimeVue 4 (Aura). Select and MultiSelect store option ids, DatePicker is bound through a computed that
     keeps an ISO string in the state (the component wants a Date), Slider a number, AutoComplete a string picked from
     static suggestions, InputText a string. -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Slider from 'primevue/slider'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const DESTINATIONS = [{ id: 'lis', name: 'Lisbon' }, { id: 'rom', name: 'Rome' }, { id: 'osl', name: 'Oslo' }]
const ACTIVITIES = [{ id: 'hiking', name: 'Hiking' }, { id: 'museums', name: 'Museums' }, { id: 'food', name: 'Food tours' }, { id: 'beach', name: 'Beach' }]
const AIRLINES = ['Lufthansa', 'Air France', 'KLM', 'TAP Air Portugal', 'ITA Airways']

const form = reactive({ traveller: '', destination: null as string | null, activities: [] as string[], start: null as string | null,
                        budget: 1000, airline: '' })

const pad = (n: number) => String(n).padStart(2, '0')
const start = computed<Date | null>({   // the state keeps "YYYY-MM-DD"; the DatePicker wants a local Date
  get: () => { if (!form.start) return null; const [y, m, d] = form.start.split('-').map(Number); return new Date(y, m - 1, d) },
  set: (d) => { form.start = d ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` : null },
})
const suggestions = ref<string[]>([])
const search = (e: { query: string }) => { suggestions.value = AIRLINES.filter((a) => a.toLowerCase().includes(e.query.toLowerCase())) }

const schema = {
  id: 'vue_primevue', title: 'Trip request',
  sections: [{ name: 'trip', label: 'Trip', fields: [
    { name: 'traveller', label: 'Traveller', required: true },
    { name: 'destination', label: 'Destination', type: 'select' as const, options: DESTINATIONS, required: true },
    { name: 'activities', label: 'Activities', type: 'multiselect' as const, options: ACTIVITIES },
    { name: 'start', label: 'Start date', type: 'date' as const, help: 'YYYY-MM-DD' },
    { name: 'budget', label: 'Budget (EUR)', type: 'number' as const, help: '0 to 5000, in steps of 100' },
    { name: 'airline', label: 'Airline', help: AIRLINES.join(', ') },
  ] }],
}
const { plugins, ready, error } = useFormguide(form, schema)
expose('primevue', { values: () => ({ ...form }), ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label data-name="traveller">Traveller <InputText v-model="form.traveller" name="traveller" /></label>
      <div data-name="destination" class="field">Destination
        <Select v-model="form.destination" :options="DESTINATIONS" option-label="name" option-value="id" placeholder="Choose" input-id="destination" />
      </div>
      <div data-name="activities" class="field">Activities
        <MultiSelect v-model="form.activities" :options="ACTIVITIES" option-label="name" option-value="id" placeholder="Choose" input-id="activities" />
      </div>
      <div data-name="start" class="field">Start date
        <DatePicker v-model="start" date-format="yy-mm-dd" input-id="start" name="start" />
      </div>
      <div data-name="budget" class="field">Budget: <span class="budget">{{ form.budget }}</span> EUR
        <Slider v-model="form.budget" :min="0" :max="5000" :step="100" />
      </div>
      <div data-name="airline" class="field">Airline
        <AutoComplete v-model="form.airline" :suggestions="suggestions" input-id="airline" name="airline" @complete="search" />
      </div>
    </form>
    <p v-if="error" class="adapter-error">{{ error }}</p>
    <agui-chat mode="inline" url="/agent/run" typing="plain" persist-thread="off" lang="en" :plugins.prop="plugins"></agui-chat>
  </main>
</template>

<style>
body { margin: 0; font: 15px system-ui, sans-serif; }
.page { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; padding: 16px; }
@media (min-width: 900px) { .page { grid-template-columns: 1fr 420px; } }
.form { display: grid; gap: 16px; }
.form label, .form .field { display: grid; gap: 6px; }
agui-chat { display: block; height: 70vh; }
</style>

<!-- Stand: Quasar 2 as a Vue plugin. q-select (emit-value: the id), q-select multiple (an array of ids), q-input with
     a q-date popup (q-date keeps "YYYY-MM-DD" by its mask), q-slider (a number), q-input (a string). -->
<script setup lang="ts">
import { reactive } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const PLANS = [{ id: 'basic', name: 'Basic' }, { id: 'plus', name: 'Plus' }, { id: 'pro', name: 'Pro' }]
const ADDONS = [{ id: 'backup', name: 'Backup' }, { id: 'support', name: 'Priority support' }, { id: 'sso', name: 'Single sign-on' }]

const form = reactive({ company: '', plan: null as string | null, addons: [] as string[], start: '', seats: 5 })

const schema = {
  id: 'vue_quasar', title: 'Subscription',
  sections: [{ name: 'subscription', label: 'Subscription', fields: [
    { name: 'company', label: 'Company', required: true },
    { name: 'plan', label: 'Plan', type: 'select' as const, options: PLANS, required: true },
    { name: 'addons', label: 'Add-ons', type: 'multiselect' as const, options: ADDONS },
    { name: 'start', label: 'Start date', type: 'date' as const, help: 'YYYY-MM-DD' },
    { name: 'seats', label: 'Seats', type: 'number' as const, help: '1 to 50' },
  ] }],
}
const { plugins, ready, error } = useFormguide(form, schema)
expose('quasar', { values: () => ({ ...form }), ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <div data-name="company"><q-input v-model="form.company" name="company" label="Company" outlined /></div>
      <div data-name="plan">
        <q-select v-model="form.plan" :options="PLANS" option-value="id" option-label="name" emit-value map-options label="Plan" outlined />
      </div>
      <div data-name="addons">
        <q-select v-model="form.addons" :options="ADDONS" option-value="id" option-label="name" emit-value map-options multiple label="Add-ons" outlined />
      </div>
      <div data-name="start">
        <q-input v-model="form.start" name="start" label="Start date" outlined>
          <template #append>
            <q-btn flat dense no-caps label="Pick">
              <q-popup-proxy><q-date v-model="form.start" mask="YYYY-MM-DD" /></q-popup-proxy>
            </q-btn>
          </template>
        </q-input>
      </div>
      <div data-name="seats">Seats: <span class="seats">{{ form.seats }}</span>
        <q-slider v-model="form.seats" :min="1" :max="50" :step="1" />
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
agui-chat { display: block; height: 70vh; }
</style>

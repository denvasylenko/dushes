<!-- Stand: the form lives in a Pinia store. v-model on the store, a getter for the regions of the country, a watcher that
     clears a region the new country lacks, and an action that recalculates the price. The adapter's source is the store. -->
<script setup lang="ts">
import { watch } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'
import { useBooking } from './store'

const store = useBooking()
watch(() => store.country, () => { if (!store.regions.includes(store.region)) store.region = '' })
watch(() => [store.plan, store.guests, store.insurance], () => store.recalc())

const schema = {
  id: 'vue_pinia', title: 'Trip booking',
  sections: [{ name: 'trip', label: 'Trip', fields: [
    { name: 'name', label: 'Full name', required: true },
    { name: 'email', label: 'Email', required: true },
    { name: 'country', label: 'Country', type: 'select' as const, options: [{ id: 'de', name: 'Germany' }, { id: 'fr', name: 'France' }, { id: 'it', name: 'Italy' }], required: true },
    { name: 'region', label: 'Region', type: 'select' as const, options: () => store.regions, visible: (v: Record<string, unknown>) => !!v.country },
    { name: 'plan', label: 'Plan', type: 'radio' as const, options: [{ id: 'basic', name: 'Basic' }, { id: 'plus', name: 'Plus' }, { id: 'pro', name: 'Pro' }] },
    { name: 'guests', label: 'Guests', type: 'number' as const, help: '1 to 10' },
    { name: 'insurance', label: 'Add travel insurance', type: 'bool' as const },
  ] }],
}
const { plugins, ready, error } = useFormguide(store, schema)
expose('pinia', { values: () => ({ ...store.$state, regions: store.regions }), ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label data-name="name">Full name <input v-model="store.name" name="name" /></label>
      <label data-name="email">Email <input v-model="store.email" name="email" type="email" /></label>
      <label data-name="country">Country
        <select v-model="store.country" name="country"><option value="">Choose</option><option value="de">Germany</option><option value="fr">France</option><option value="it">Italy</option></select>
      </label>
      <label v-if="store.country" data-name="region">Region
        <select v-model="store.region" name="region"><option value="">Choose</option><option v-for="r in store.regions" :key="r" :value="r">{{ r }}</option></select>
      </label>
      <fieldset data-name="plan"><legend>Plan</legend>
        <label v-for="p in ['basic', 'plus', 'pro']" :key="p"><input v-model="store.plan" type="radio" name="plan" :value="p" /> {{ p }}</label>
      </fieldset>
      <label data-name="guests">Guests <input v-model.number="store.guests" name="guests" type="number" min="1" max="10" /></label>
      <label data-name="insurance"><input v-model="store.insurance" name="insurance" type="checkbox" /> Add travel insurance</label>
      <p class="total">Price: {{ store.price }} EUR</p>
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
.form fieldset label { display: inline-flex; gap: 6px; margin-right: 12px; }
agui-chat { display: block; height: 70vh; }
</style>

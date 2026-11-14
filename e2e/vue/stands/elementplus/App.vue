<!-- Stand: Element Plus. The library's own components bound to reactive state with v-model: el-select (single),
     el-select multiple, el-date-picker (value-format YYYY-MM-DD), el-slider and a filterable el-select with static
     options (autocomplete-like), next to a plain el-input. data-name sits on each component's root (el-input and el-date-picker: on the field box, as
     el-input moves attrs to its inner input and el-date-picker drops them). -->
<script setup lang="ts">
import { reactive } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const COUNTRIES = [{ id: 'de', name: 'Germany' }, { id: 'fr', name: 'France' }, { id: 'it', name: 'Italy' }]
const LANGUAGES = [{ id: 'en', name: 'English' }, { id: 'de', name: 'German' }, { id: 'fr', name: 'French' }, { id: 'it', name: 'Italian' }]
const CITIES = [{ id: 'ber', name: 'Berlin' }, { id: 'par', name: 'Paris' }, { id: 'rom', name: 'Rome' }, { id: 'mun', name: 'Munich' }]
const form = reactive({ name: '', country: '', languages: [] as string[], start: '', budget: 20, city: '' })

const schema = {
  id: 'vue_elementplus', title: 'Trip request',
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
expose('elementplus', { values: () => ({ ...form }), ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label class="field" data-name="name">Full name <el-input v-model="form.name" name="name" /></label>
      <div class="field">Country
        <el-select v-model="form.country" data-name="country" placeholder="Choose">
          <el-option v-for="o in COUNTRIES" :key="o.id" :value="o.id" :label="o.name" />
        </el-select>
      </div>
      <div class="field">Languages
        <el-select v-model="form.languages" multiple data-name="languages" placeholder="Choose">
          <el-option v-for="o in LANGUAGES" :key="o.id" :value="o.id" :label="o.name" />
        </el-select>
      </div>
      <!-- el-date-picker drops data-name (its attrs go nowhere on the root), so the field box carries it -->
      <div class="field" data-name="start">Start date
        <el-date-picker v-model="form.start" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="Pick a day" />
      </div>
      <div class="field">Budget (hundreds of EUR)
        <el-slider v-model="form.budget" :min="0" :max="100" :step="5" show-input data-name="budget" />
      </div>
      <div class="field">City
        <el-select v-model="form.city" filterable data-name="city" placeholder="Type a city">
          <el-option v-for="o in CITIES" :key="o.id" :value="o.id" :label="o.name" />
        </el-select>
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
.form { display: grid; gap: 12px; }
.field { display: grid; gap: 4px; }
agui-chat { display: block; height: 70vh; }
</style>

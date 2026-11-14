<!-- Stand: Vuelidate 2. reactive state with v-model, useVuelidate with required, numeric + between (seats), sameAs
     (the confirmed password) and requiredIf (the company name, only for a business account). The adapter writes the
     reactive state, runs v$.$validate() after every write and sends v$.$errors with the config. -->
<script setup lang="ts">
import { computed, reactive } from 'vue'
import useVuelidate from '@vuelidate/core'
import { between, helpers, numeric, required, requiredIf, sameAs } from '@vuelidate/validators'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const form = reactive({ name: '', seats: 1, password: '', confirm: '', business: false, company: '' })
const rules = computed(() => ({
  name: { required: helpers.withMessage('Enter your name', required) },
  seats: { required, numeric: helpers.withMessage('Enter a number', numeric), between: helpers.withMessage('From 1 to 50 seats', between(1, 50)) },
  password: { required: helpers.withMessage('Choose a password', required) },
  confirm: { required: helpers.withMessage('Repeat the password', required), sameAs: helpers.withMessage('The passwords differ', sameAs(form.password)) },
  company: { requiredIf: helpers.withMessage('Enter the company name', requiredIf(() => form.business)) },
}))
const v$ = useVuelidate(rules, form)

const schema = {
  id: 'vue_vuelidate', title: 'Team plan',
  sections: [{ name: 'plan', label: 'Plan', fields: [
    { name: 'name', label: 'Full name', required: true },
    { name: 'seats', label: 'Seats', type: 'number' as const, required: true, help: '1 to 50' },
    { name: 'password', label: 'Password', required: true },
    { name: 'confirm', label: 'Repeat the password', required: true },
    { name: 'business', label: 'This is a business account', type: 'bool' as const },
    { name: 'company', label: 'Company name', required: (v: Record<string, unknown>) => !!v.business, visible: (v: Record<string, unknown>) => !!v.business },
  ] }],
}
/** Vuelidate's errors, one message per field (the first). */
const errors = () => {
  const out: Record<string, string> = {}
  for (const e of v$.value.$errors) if (!out[e.$property]) out[e.$property] = String(e.$message)
  return out
}
const { plugins, ready, error } = useFormguide(form, schema, { validate: () => v$.value.$validate(), errors })
expose('vuelidate', { values: () => ({ ...form }), errors, ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label data-name="name">Full name <input v-model="form.name" name="name" /></label>
      <label data-name="seats">Seats <input v-model.number="form.seats" name="seats" type="number" min="1" max="50" /></label>
      <label data-name="password">Password <input v-model="form.password" name="password" type="password" /></label>
      <label data-name="confirm">Repeat the password <input v-model="form.confirm" name="confirm" type="password" /></label>
      <label data-name="business"><input v-model="form.business" name="business" type="checkbox" /> This is a business account</label>
      <label v-if="form.business" data-name="company">Company name <input v-model="form.company" name="company" /></label>
      <ul class="err"><li v-for="e in v$.$errors" :key="e.$uid">{{ e.$property }}: {{ e.$message }}</li></ul>
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
.err { color: #c00; font-size: 13px; }
agui-chat { display: block; height: 70vh; }
</style>

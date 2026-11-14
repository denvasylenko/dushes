<!-- Stand: VeeValidate 4. useForm with a rules object (required, email, at least 18 from the birth date) and useField
     for each input (v-model on the field's value). The adapter reads form.values, writes with setFieldValue, runs
     form.validate() after every write and sends form.errors with the config. -->
<script setup lang="ts">
import { useField, useForm } from 'vee-validate'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const EMAIL = /^\S+@\S+\.\S+$/
/** Full years from an ISO date (YYYY-MM-DD) to today. */
function age(iso: string): number {
  const b = new Date(`${iso}T00:00:00`), now = new Date()
  let y = now.getFullYear() - b.getFullYear()
  if (now.getMonth() < b.getMonth() || (now.getMonth() === b.getMonth() && now.getDate() < b.getDate())) y--
  return y
}
const rules = {
  name: (v: string) => !!v?.trim() || 'Enter your name',
  email: (v: string) => (!v ? 'Enter your email' : EMAIL.test(v) || 'Enter a valid email'),
  birthDate: (v: string) => (!v ? 'Enter your birth date' : (/^\d{4}-\d{2}-\d{2}$/.test(v) && !isNaN(age(v))) ? age(v) >= 18 || 'You must be at least 18' : 'Enter a date'),
}
const form = useForm({ validationSchema: rules, initialValues: { name: '', email: '', birthDate: '', newsletter: false } })
const { value: name } = useField<string>('name')
const { value: email } = useField<string>('email')
const { value: birthDate } = useField<string>('birthDate')
const { value: newsletter } = useField<boolean>('newsletter')

const schema = {
  id: 'vue_veevalidate', title: 'Account',
  sections: [{ name: 'account', label: 'Account', fields: [
    { name: 'name', label: 'Full name', required: true },
    { name: 'email', label: 'Email', required: true },
    { name: 'birthDate', label: 'Birth date', type: 'date' as const, required: true, help: 'You must be 18 or older' },
    { name: 'newsletter', label: 'Send me the newsletter', type: 'bool' as const },
  ] }],
}
/** VeeValidate's errors without the empty entries. */
const errors = () => Object.fromEntries(Object.entries(form.errors.value).filter(([, m]) => !!m)) as Record<string, string>
const source = { getValues: () => ({ ...form.values }), setValue: (n: string, v: unknown) => form.setFieldValue(n as 'name', v as string) }
const { plugins, ready, error } = useFormguide(source, schema, { validate: async () => (await form.validate()).valid, errors })
expose('veevalidate', { values: () => ({ ...form.values }), errors, ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label data-name="name">Full name <input v-model="name" name="name" /><span class="err">{{ form.errors.value.name }}</span></label>
      <label data-name="email">Email <input v-model="email" name="email" type="email" /><span class="err">{{ form.errors.value.email }}</span></label>
      <label data-name="birthDate">Birth date <input v-model="birthDate" name="birthDate" type="date" /><span class="err">{{ form.errors.value.birthDate }}</span></label>
      <label data-name="newsletter"><input v-model="newsletter" name="newsletter" type="checkbox" /> Send me the newsletter</label>
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
.err { color: #c00; font-size: 13px; min-height: 1em; }
agui-chat { display: block; height: 70vh; }
</style>

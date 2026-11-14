<script setup lang="ts">
import { form, PLANS } from './store'
</script>
<template>
  <fieldset class="step" data-step="extras"><legend>Step 3: Plan</legend>
    <label data-name="plan">Plan
      <select v-model="form.plan" name="plan"><option :value="null">Choose</option><option v-for="p in PLANS" :key="p.id" :value="p.id">{{ p.name }}</option></select>
    </label>
    <label data-name="start">Start date <input v-model="form.start" name="start" type="date" /></label>
    <label data-name="notes">Notes <textarea v-model="form.notes" name="notes"></textarea></label>
  </fieldset>
</template>

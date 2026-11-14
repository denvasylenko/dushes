<script setup lang="ts">
import { form } from './store'
</script>
<template>
  <fieldset class="step" data-step="address"><legend>Step 2: Address</legend>
    <label data-name="street">Street <input v-model="form.street" name="street" /></label>
    <label data-name="city">City <input v-model="form.city" name="city" /></label>
  </fieldset>
</template>

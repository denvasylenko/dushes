<script setup lang="ts">
import { form } from './store'
</script>
<template>
  <fieldset class="step" data-step="personal"><legend>Step 1: You</legend>
    <label data-name="name">Full name <input v-model="form.name" name="name" /></label>
    <label data-name="email">Email <input v-model="form.email" name="email" type="email" /></label>
  </fieldset>
</template>

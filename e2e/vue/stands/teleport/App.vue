<!-- Stand: some fields live in a modal rendered with <Teleport to="body">, opened by a button and unmounted when
     closed (v-if). A card writes the modal's fields whether it is open or not; "take me there" to a modal field opens
     it (onReveal) and the highlight finds the field in the teleported DOM. -->
<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const form = reactive({ name: '', product: '', address: '', city: '', phone: '' })
const open = ref(false)

const schema = {
  id: 'vue_teleport', title: 'Order',
  sections: [
    { name: 'order', label: 'Order', fields: [
      { name: 'name', label: 'Full name', required: true },
      { name: 'product', label: 'Product' },
    ] },
    { name: 'delivery', label: 'Delivery details', fields: [
      { name: 'address', label: 'Address' },
      { name: 'city', label: 'City' },
      { name: 'phone', label: 'Phone' },
    ] },
  ],
}
const onReveal = async (section: string) => { if (section === 'delivery') { open.value = true; await nextTick() } }
const { plugins, ready, error } = useFormguide(form, schema, { onReveal })
expose('teleport', { values: () => ({ ...form, modalOpen: open.value }), ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label data-name="name">Full name <input v-model="form.name" name="name" /></label>
      <label data-name="product">Product <input v-model="form.product" name="product" /></label>
      <button type="button" class="open-delivery" @click="open = true">Delivery details</button>
      <p class="summary">{{ form.address || 'No address' }}{{ form.city ? `, ${form.city}` : '' }}</p>
    </form>
    <Teleport to="body">
      <div v-if="open" class="modal-backdrop">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delivery-title">
          <h2 id="delivery-title">Delivery details</h2>
          <label data-name="address">Address <input v-model="form.address" name="address" /></label>
          <label data-name="city">City <input v-model="form.city" name="city" /></label>
          <label data-name="phone">Phone <input v-model="form.phone" name="phone" type="tel" /></label>
          <button type="button" class="close" @click="open = false">Done</button>
        </div>
      </div>
    </Teleport>
    <p v-if="error" class="adapter-error">{{ error }}</p>
    <agui-chat mode="inline" url="/agent/run" typing="plain" persist-thread="off" lang="en" :plugins.prop="plugins"></agui-chat>
  </main>
</template>

<style>
body { margin: 0; font: 15px system-ui, sans-serif; }
.page { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; padding: 16px; }
@media (min-width: 900px) { .page { grid-template-columns: 1fr 420px; } }
.form { display: grid; gap: 12px; }
.form label, .modal label { display: grid; gap: 4px; }
/* the modal covers the form, not the chat: the person keeps talking while it is open (the form keeps room for it) */
.form { min-height: 380px; align-content: start; }
.modal-backdrop { position: absolute; inset: 0 auto auto 0; width: min(100vw, 480px); padding: 16px; box-sizing: border-box; z-index: 10; }
.modal { display: grid; gap: 12px; padding: 16px; border-radius: 12px; background: #fff; box-shadow: 0 8px 32px rgba(0, 0, 0, .2); }
agui-chat { display: block; height: 70vh; }
</style>

<!-- Stand: dynamic rows. An invoice whose lines are an array (items: [{desc, qty, price}]) with "Add row" and a
     computed total. The layout has no repeated rows yet, so the schema declares a fixed number of row slots by their
     dotted names ("items.0.qty"), each shown while its row exists; the adapter writes the dotted path. -->
<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useFormguide } from '@formguide/agui-chat/vue'
import { expose } from '../../src/stand'

const SLOTS = 5   // rows the layout can address today
type Row = { desc: string; qty: number; price: number }
const blank = (): Row => ({ desc: '', qty: 1, price: 0 })
const form = reactive({ customer: '', items: [blank(), blank()] as Row[] })
const total = computed(() => form.items.reduce((s, r) => s + (Number(r.qty) || 0) * (Number(r.price) || 0), 0))
const addRow = () => form.items.push(blank())

const exists = (i: number) => (v: Record<string, unknown>) => Array.isArray(v.items) && v.items.length > i
const schema = {
  id: 'vue_rows', title: 'Invoice', layout: 'sections' as const,
  sections: [
    { name: 'billing', label: 'Billing', fields: [{ name: 'customer', label: 'Customer', required: true }] },
    { name: 'lines', label: 'Lines', fields: Array.from({ length: SLOTS }, (_, i) => [
      { name: `items.${i}.desc`, label: `Row ${i + 1}: description`, visible: exists(i) },
      { name: `items.${i}.qty`, label: `Row ${i + 1}: quantity`, type: 'number' as const, visible: exists(i) },
      { name: `items.${i}.price`, label: `Row ${i + 1}: unit price`, type: 'number' as const, visible: exists(i) },
    ]).flat() },
  ],
}
const { plugins, ready, error } = useFormguide(form, schema)
expose('rows', { values: () => ({ ...form, total: total.value }), ready, error })
</script>

<template>
  <main class="page">
    <form class="form" @submit.prevent>
      <label data-name="customer">Customer <input v-model="form.customer" name="customer" /></label>
      <table class="lines">
        <thead><tr><th>Description</th><th>Qty</th><th>Price</th><th>Sum</th></tr></thead>
        <tbody>
          <tr v-for="(row, i) in form.items" :key="i" :data-row="i">
            <td :data-name="`items.${i}.desc`"><input v-model="row.desc" :name="`items.${i}.desc`" :aria-label="`Row ${i + 1} description`" /></td>
            <td :data-name="`items.${i}.qty`"><input v-model.number="row.qty" :name="`items.${i}.qty`" type="number" min="0" :aria-label="`Row ${i + 1} quantity`" /></td>
            <td :data-name="`items.${i}.price`"><input v-model.number="row.price" :name="`items.${i}.price`" type="number" min="0" step="0.01" :aria-label="`Row ${i + 1} price`" /></td>
            <td class="sum">{{ (Number(row.qty) || 0) * (Number(row.price) || 0) }}</td>
          </tr>
        </tbody>
      </table>
      <button type="button" class="add" @click="addRow">Add row</button>
      <p class="total">Total: {{ total }} EUR</p>
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
.lines { width: 100%; border-collapse: collapse; }
.lines input { width: 100%; box-sizing: border-box; }
agui-chat { display: block; height: 70vh; }
</style>

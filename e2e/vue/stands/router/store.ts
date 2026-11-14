/** The form's state: one reactive object outside the router views, so it lives across steps. */
import { reactive } from 'vue'

export const form = reactive({ name: '', email: '', street: '', city: '', plan: null as string | null, start: '', notes: '' })
export const PLANS = [{ id: 'monthly', name: 'Monthly' }, { id: 'yearly', name: 'Yearly' }]
export const STEPS = [{ name: 'personal', label: 'You' }, { name: 'address', label: 'Address' }, { name: 'extras', label: 'Plan' }]

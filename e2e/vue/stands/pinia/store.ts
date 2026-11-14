/** The booking form as a Pinia option store: state, a getter (regions of the country) and an action (the price). */
import { defineStore } from 'pinia'

export const REGIONS: Record<string, string[]> = { de: ['Bavaria', 'Berlin', 'Hesse'], fr: ['Brittany', 'Normandy', 'Provence'], it: ['Lazio', 'Tuscany'] }
export const RATES: Record<string, number> = { basic: 20, plus: 35, pro: 50 }

export const useBooking = defineStore('booking', {
  state: () => ({ name: '', email: '', country: '', region: '', plan: 'basic', guests: 1, insurance: false, price: 20, recalcs: 0 }),
  getters: {
    regions: (s): string[] => REGIONS[s.country] ?? [],
  },
  actions: {
    /** The price from the plan, the guests and the insurance; counts its runs (the tests check that it ran). */
    recalc() {
      this.price = (RATES[this.plan] ?? 0) * this.guests + (this.insurance ? 10 : 0)
      this.recalcs++
    },
  },
})

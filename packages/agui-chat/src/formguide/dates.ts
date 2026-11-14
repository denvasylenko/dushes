/** Small date helpers shared by the calendar (in the blocks script) and the date field (in the chat). */
export interface DateLimits { min?: string | null; max?: string | null }

export const pad = (n: number) => String(n).padStart(2, '0')
export const isoOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const parse = (s?: string | null) => (s && /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(`${s}T00:00:00`) : null)

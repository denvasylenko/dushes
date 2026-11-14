/** Which numbers are names, not amounts: shown as written, never with a thousands separator ("2019", not "2,019"). */

// whole words of a field name that make its number a name: a year, a zip, a phone, an id
const NAME_WORDS = new Set(['year', 'yr', 'zip', 'zipcode', 'postal', 'postcode', 'code', 'pin', 'phone', 'tel', 'id', 'vin', 'inn', 'iban'])

/** By the field's format (`year`, `code`) or a whole word of its name (`year_of_manufacture`, `buildYear`, `zip`). */
export function isPlainNumber(name: string | undefined, format?: unknown): boolean {
  if (['year', 'code'].includes(String(format))) return true
  const words = String(name ?? '').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase().split(/[^a-z0-9]+/)
  return words.some((w) => NAME_WORDS.has(w))
}

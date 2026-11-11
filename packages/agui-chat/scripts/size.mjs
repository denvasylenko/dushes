// Fails the build when the one-script bundle grows past the budget (gzipped).
import { readFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'

const BUDGET = 40 * 1024
const file = new URL('../dist/agui-chat.iife.js', import.meta.url)
const size = gzipSync(readFileSync(file)).length
console.log(`agui-chat.iife.js: ${(size / 1024).toFixed(1)} KB gzipped (budget ${BUDGET / 1024} KB)`)
if (size > BUDGET) process.exit(1)

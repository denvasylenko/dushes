// Fails the build when the one-script bundle grows past the budget (gzipped).
import { readFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'

// 45 KB since the card kit and our own pickers (2026-11-12)
// 48 KB since the customization API (parts, component tokens, slots; 2026-11-12)
// 42 KB since the languages other than English moved to packs loaded on demand (src/lang, 2026-11-13: 48.2 -> 39.4 KB)
const BUDGET = 42 * 1024
const file = new URL('../dist/agui-chat.iife.js', import.meta.url)
const size = gzipSync(readFileSync(file)).length
console.log(`agui-chat.iife.js: ${(size / 1024).toFixed(1)} KB gzipped (budget ${BUDGET / 1024} KB)`)
if (size > BUDGET) process.exit(1)

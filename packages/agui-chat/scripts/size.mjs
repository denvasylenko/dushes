// Fails the build when the one-script bundle grows past the budget (gzipped).
import { readFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'

// 45 KB since the card kit and our own pickers (2026-11-12)
// 48 KB since the customization API (parts, component tokens, slots; 2026-11-12)
// 42 KB since the languages other than English moved to packs loaded on demand (src/lang, 2026-11-13: 48.2 -> 39.4 KB)
// 43 KB since server dictation (Owner) filled 42 KB and cards that wait for their text plus on-demand theme packs added the rest (2026-11-14); the themes themselves stay out of the bundle
// 46 KB since cards from blocks (16 small parts that compose any card, formguide/blocks.ts, 2026-11-14): +3.6 KB;
// they can move to an on-demand file like the themes if the budget gets tight again
// 47 KB since the host hooks for Herefront (removeMessage, updateCard, onAction, follow on restore, agui:applied; 2026-11-14)
const BUDGET = 47 * 1024
const file = new URL('../dist/agui-chat.iife.js', import.meta.url)
const size = gzipSync(readFileSync(file)).length
console.log(`agui-chat.iife.js: ${(size / 1024).toFixed(1)} KB gzipped (budget ${BUDGET / 1024} KB)`)
if (size > BUDGET) process.exit(1)

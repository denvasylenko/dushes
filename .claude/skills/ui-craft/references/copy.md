# Interface text

Languages: the widget has 7 (en, ru, uk, de, fr, it, es) in `packages/agui-chat/src/i18n.ts` and `src/formguide/i18n.ts`, generated from one table; every key exists in every language, and non-ASCII text is written as `\u` escapes (the repository is English-only). The demo, the examples and the docs are English. New text goes in all languages of its surface at once.

## Rules

1. **A button = a verb + an object, the result, not the mechanics.** "Fill in 2 fields", "Upload a file", "Cancel booking". Not "OK", "Yes", "Apply", "Submit". A dangerous button repeats the object.
2. **The person's language, not the protocol's.** Not "interrupt", "jsx_hash", "AG-UI", "SSE", "run", "tool call", "thread"; but "question", "your form", "the assistant", "conversation".
3. **Short.** A title is 1–4 words, a hint one sentence. Cut "please", "just", "simply".
4. **One concept, one word everywhere.** "Fill in" (not "apply" on one card and "set" on another), "Skip", "Undo", "Steps".
5. **Numbers.** Separators by locale, correct plurals ("1 step", "3 steps"), no "1 steps".
6. **Success is silent or a short fact** ("Filled in", "Uploaded: passport.pdf"). No exclamation marks.
7. **An error does not blame the person** and says what to do: "The assistant is not reachable. Check your connection and press Try again."
8. **Hints explain why, not what**: "Drop a photo of the page with your details", not "File upload area".
9. **An empty state invites**: "Ask anything, or pick a suggestion."
10. **Tone**: the widget speaks to end users of someone else's product: warm, plain, no technical words; the docs speak to developers: precise and direct.

## Replacements

| Before | After |
| --- | --- |
| Something went wrong. HTTP 500: <server text> | The assistant could not answer. Try again in a moment. [Try again] |
| Are you sure? | (do it at once + Undo) |
| Fill in (for 1 of 3 ticked) | Fill in 1 of 3 |
| 1 steps | Steps: 1 |
| A disabled Send with no reason | Send stays active; with nothing to send, the composer shakes |

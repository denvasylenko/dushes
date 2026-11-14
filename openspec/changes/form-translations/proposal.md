# Proposal

Status: proposal (CPO, 2026-11-14: cards in the conversation's language; point 3, the form's own translations).

## Why

A card's labels follow the conversation's language. Since this change the agent translates what the form writes in one language. A form that already has translated labels (many bank and government forms do) should be used as it is: the business's own words are better than a model's translation, and they cost no tokens.

## What Changes

- **Config**: a field's props MAY carry `i18n: {<lang>: {label?, placeholder?, hint?}}` (two-letter codes); an option object MAY carry `names: {<lang>: "..."}` next to its `name`. Nothing else in the contract changes; a form without them works as today.
- **The agent's view**: a field card lists the languages the form has ("labels: ru, de"), so the agent knows when not to translate.
- **Cards**: `ask_user` and `propose_changes` take an optional `language` (two letters, the conversation's). When the form has that language, the server fills each label, option name and placeholder from the form; the agent's own label is used only where the form has none. The value sent to the form never changes.
- **The conversation's language for the widget** (agreed with the widget designer): one `CUSTOM language {lang}` event per run, as soon as the language is known and only when it changes: at run start from a cheap check of the user's message (script and a few function words; sent only when confident), else when the agent first passes `language`. The last known language is kept per thread and returned on restore. The widget switches its card words, the steps line and suggestions to it for this chat; the chat's frame stays in the page's language.

## The language as a setting, no model needed (owner, via the CPO)

The main path needs no model at all:

- **The host or the form sets the language**: `language` (one) or `languages` (allowed ones) on the host's FormGuide / Dushes config and on a form (`props[form].language`), set by the developer. When it is set, the conversation's language is not guessed.
- **The widget's own words** come from its language packs (no model).
- **Labels and options** come from the form's `i18n` and option `names` (no model).
- **A model translation is only the fallback** for strings the form has no translation for, and a setting turns it off: `translate_missing: true | false` (default true). With it off, a missing translation shows the form's own words.
- **Detecting the language from the conversation** happens only when no language is set.
- The docs show the main path first: set the language and the form's translations, and the cards cost no model calls.

## The server guarantees the language (CPO, after SRE's check on v9)

The model alone does not keep cards in the user's language (hosted Haiku at low effort left a German conversation's fill card in English). So the server enforces it:

- **The conversation's language**: `formguide/language.py` detects it from the user's messages (script, then a few function words per language; en, ru, uk, de, fr, es, it), keeps the last confident one per thread, and lets the agent's `language` argument override it.
- **Every card is checked before it is sent**: the question, option labels, row labels, notes and shown values. A string in another language than the conversation's is replaced first from the form's own translation (`i18n`, option `names`), else translated in one batched call to the cheap model role, cached per (language, text) so a form's labels are translated once. Values sent to the form never change; numbers, names and the user's own words are left as they are.
- **The card says its language** (`language` on the payload) and the run emits `CUSTOM language {lang}`, so the widget's own words follow it.
- **A failure never blocks the card**: if the translation call fails or times out (2 s), the card goes out as it is and the failure is logged.
- **Counted like every model call** (SRE): the translation call reports its model and tokens through run_stats (kind `translate`), so the public demo's cost cap counts it. The cache is in memory and may be empty after a restart; nothing depends on it surviving one.

## Capabilities

### Modified Capabilities
- `form-layout`: translated labels and option names in the config.

## Impact

`form/overlay.py` (read i18n and names), `form/render.py` (the languages line), `agent/tools.py` (the `language` argument, labels from the form), docs (connect-your-form, the cards page), QA: a ru user on a form with ru labels sees the form's words, not the agent's.

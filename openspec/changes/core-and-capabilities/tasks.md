# Tasks

## 1. Names and aliases (0.4)
- [ ] `UIAgent` (from `FormGuide`), `Researcher`; aliases `FormGuide`, `SiteGuide` with a DeprecationWarning; the old import paths keep working
- [ ] docs labels (Docs Lead), a migration note for the cabinet

## 2. The core
- [ ] `Core` with knowledge, models, memory, transcripts, attachments, transcription; `UIAgent(core)`; `FormGuide(config)` = `UIAgent(Core(config))`
- [ ] `Dushes(core, site_map, ui=None)`; `Dushes(form_guide, site)` still works
- [ ] `capabilities:` in config (know, show, fill, do, analyze); a knowledge-only site in the demo

## 3. Do and Analyze
- [ ] `HostAction` with undo or a confirm card; Analyze tools with chart and table cards

## 4. Declared forms
- [ ] the declaration (steps, groups, fields, when, options or a resolver); the server-side state and recompute
- [ ] parent changes: keep valid values, clear invalid with Restore; the sheet for long forms (UI/UX)

## 5. The Researcher
- [ ] toolsets; `documents` as today; the `data` toolset behind a sandbox hook (opt-in)

## 6. The submit guard
- [ ] submitting tools unbound until review passes; run only on the summary card's resume

Every phase: tests, specs, docs, QA's evals with the held-out domain.

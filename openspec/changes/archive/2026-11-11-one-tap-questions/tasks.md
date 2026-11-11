# Tasks

## 1. Backend

- [x] 1.1 `ask_user`: `applies`, the encoded `value` per option, `previous` for an editable choice field.
- [x] 1.2 `confirm` ask branch: a resume with `config` counts as applied (diff, snapshot, text); the transcript records `applied`.
- [x] 1.3 Prompt rule: a question with `field` fills it; do not propose it again.
- [x] 1.4 Tests: payload encoding (default and id-only components), the applied resume, the fallback without config, a locked field.

## 2. Widget

- [x] 2.1 The question card applies answers (single and multiple), shows "✓ label · Undo", handles `applyChanges` errors.
- [x] 2.2 Field card: "Fill in N fields" with plurals in seven languages.
- [x] 2.3 Styles: type and radius scales, classes instead of inline styles in cards, 44 px touch targets, a soft focus ring, no script focus on touch, a quiet empty send button.
- [x] 2.4 Readable errors with "Try again" and a tooltip; "Still working…" after 4 s.
- [x] 2.5 Tests for 2.1–2.4.

## 3. Demo, docs, checks

- [x] 3.1 Demo title from the pack or a readable form name.
- [x] 3.2 Docs: `ui-components.md` §2.5, `chat-widget.md`; strike out what is fixed in `.claude/skills/ui-craft/references/audit.md`.
- [x] 3.3 Browser check at 390 and 1280 px, light and dark, with the gallery and a live loan conversation; screenshots.
- [x] 3.4 Run `openspec validate --all --strict`, `python3 scripts/check_english.py`, the backend and widget tests and builds; archive the change.

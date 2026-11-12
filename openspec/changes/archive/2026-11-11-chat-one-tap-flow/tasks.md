# Tasks

## 1. Backend

- [x] 1.1 Suggestions: `set` per item in the prompt and the parser; validate against the latest config in `guide.py`; `applies` in the event.
- [x] 1.2 `propose_changes`: deferred rows for choice fields without options or disabled, when other rows are valid.
- [x] 1.3 Prompt rules: decisions as cards; one sentence before a card; tool description mentions dependent fields.
- [x] 1.4 Tests: suggestions parsing and validation, deferred rows, the disabled-only case.

## 2. Widget

- [x] 2.1 Action chips: render `applies`, apply via the plugin, Undo line, error, then send.
- [x] 2.2 Field card: deferred rows applied after the others; "not available".
- [x] 2.3 Folded cards with a toggle.
- [x] 2.4 Number formatting, hidden duplicate reason, inline markdown in question text.
- [x] 2.5 Empty chat: starters kept after New chat, intro without suggestions; "Replaced by your message".
- [x] 2.6 i18n keys in seven languages; tests.

## 3. Docs and checks

- [x] 3.1 `docs/chat-widget.md`, `docs/architecture.md` (suggestions event), ui-craft audit (strike out what is fixed).
- [x] 3.2 Browser check at 390 and 1280 px, light and dark, with a live conversation.
- [x] 3.3 `openspec validate --all --strict`, `check_english.py`, backend and widget tests and builds.

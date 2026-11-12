# Tasks

## 1. Actions and capabilities

- [x] 1.1 `actions` in `GuideConfig` and `load_config` (true / false / auto, unknown keys refused)
- [x] 1.2 `agent/actions.py`: the resolver (config, auto rules, `forwardedProps.capabilities`) and the capability table
- [x] 1.3 Bind only the resolved tools in `llm`; ToolError for a call to an unbound tool
- [x] 1.4 Prompt rules per action in `system_prompt` (left out when the action is off)
- [x] 1.5 Tests: an action off, auto without documents, capabilities absent / present, an old client unchanged

## 2. Question payloads

- [x] 2.1 Option `description`, `attrs` (dropped unless shared by 2 or more), `recommended`, `suggested` (checked ids)
- [x] 2.2 Field-backed questions: all options up to 500; the 12 cap only for model-written options
- [x] 2.3 Number range from the field (min / max / step / unit); the `address` input type
- [x] 2.4 `fields` (2-3 fields, needs `ask.multi`): payload, resume `answers` + config validated and taken like an accepted card
- [x] 2.5 Tests for each

## 3. Field-change payloads

- [x] 3.1 `kind` on every change
- [x] 3.2 Consents from the pack / field spec: consent rows, only ticked names applied
- [x] 3.3 Soft row issues: an optional model-written `issue` per change, shown as a warning
- [x] 3.4 Remember the last extraction per thread; `confidence` and card `source` on matching proposals
- [x] 3.5 Tests for each

## 4. Review

- [x] 4.1 `agent/review.py`: sections and issues from the overlay; warnings and fixes validated
- [x] 4.2 The review_form tool and the `review` interrupt; transcript entry and restore
- [x] 4.3 Resume `continue` / `submit` / `fixed` (the fixed path reuses the accepted-card path)
- [x] 4.4 Tests: status mid-way, submit with issues, an invalid fix dropped, fixed resume

## 5. Events, confirm, feedback, privacy

- [x] 5.1 confirm_action `details` (up to 6) and `consequence`
- [x] 5.2 CUSTOM `receipt` from a host tool's `receipt`
- [x] 5.3 CUSTOM `sources` parsed from the researcher's answer
- [x] 5.4 `POST /feedback` (204, 422) stored in the transcript
- [x] 5.5 `attachments.privacy_note` as `privacy` on upload requests
- [x] 5.6 Tests for each

## 6. Docs and wrap-up

- [x] 6.1 `site/`: reference/configuration (actions, privacy note), reference/agui-events (keys, events, capabilities), reference/http-api (feedback), concepts/turn and architecture; the landing demo script if card payloads it replays changed
- [x] 6.2 Message the UX session the final shapes and any differences from the agreed ones
- [x] 6.3 `openspec validate --all --strict`, `check_english.py`, backend tests, `cd site && npm run build`

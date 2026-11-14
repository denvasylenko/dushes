# Tasks

## 1. Configuration and storage

- [ ] 1.1 Parse `profile:` in `config.py` and `FormGuide(profile=...)` with the defaults; verify with config tests for defaults and every option
- [ ] 1.2 Add `profile.py`: get, save with time, expire, delete, consent flag; file store under `data_dir/profiles/` with hashed ids and a host-callback store; verify with unit tests
- [ ] 1.3 Read the user id per run (`header:`, `forwarded:`, callback) in `server.py`; verify with an HTTP test
- [ ] 1.4 Add the pack's `profile` map and its warnings in `domain/packs.py`; verify with the typo scenario test
- [ ] 1.5 Write `backend/profile.mdx` (with "Every option"), update `reference/configuration.md` and `backend/domain-packs.mdx`; build passes

## 2. Saving and consent

- [ ] 2.1 Save kept rows of an accepted card at the confirm node; verify with scripted-model tests for accepted, rejected and edited rows
- [ ] 2.2 Ask for consent once under `consent: ask` and honour `always` / `never`; verify with tests for each mode

## 3. Offering back and Dushes

- [ ] 3.1 Turn mapped profile values into the first run's prefill with a "from last time" note; verify the second-form scenario with a scripted model
- [ ] 3.2 Give Dushes the profile and add mapped values to `open_form` hand-offs; verify with tests in `test_site.py`
- [ ] 3.3 Update `concepts/memory.mdx` (profile vs conversation memory) and `backend/dushes.mdx`; build passes

## 4. Forgetting

- [ ] 4.1 "Forget my details" with a confirmation card, and `DELETE /profile/{user_id}`; verify with a graph test and an HTTP test
- [ ] 4.2 Document the endpoint in `reference/http-api.md` and README; build passes

## 5. Checks

- [ ] 5.1 Turn the profile on in the demo (`formguide.yaml`, loan and booking packs) and run both forms in the browser one after another; `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q`, `cd site && npm run build` pass

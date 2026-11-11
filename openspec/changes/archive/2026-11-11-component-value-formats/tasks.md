# Tasks

## 1. Field specs

- [x] 1.1 Add `FieldSpec` to `form/layout.py`. `ComponentMap.fields` accepts `str | dict | FieldSpec`, normalised in `__post_init__`; `ComponentMap.spec(tag)`. Unknown roles or keys raise `ValueError` naming the tag.
- [x] 1.2 Add the field roles `radio` and `multiselect`, and a `CHOICE = {"select", "radio"}` helper.
- [x] 1.3 `config.py`: parse field spec objects from YAML (`true`/`false` keys survive YAML booleans) and add the docstring example.

## 2. Reading and writing values

- [x] 2.1 New `form/values.py` with:
  - `read_options` (configured keys, detected pairs, list of strings, id→label object);
  - lenient `decode` per role;
  - strict `encode` per role;
  - codec loading and caching with error handling.
- [x] 2.2 `form/overlay.py`: `Eff.raw` keeps the stored value. `Eff.value` and `Eff.options` become canonical through the spec, plus `Eff.unreadable`. Update the following for `radio` and `multiselect`:
  - `filled` and `invalid_value`;
  - `display_value` and `_trigger_value`;
  - the dependency categories in the diff.
- [x] 2.3 `form/render.py`: options flags for choice and multiselect roles; ⚠ for unreadable values.
- [x] 2.4 `agent/tools.py`:
  - `_norm_value` handles `radio` and `multiselect` (a list or comma text, per-item validation) and returns canonical numbers;
  - `propose_changes` writes `value = encode(...)` with `display` from the canonical value;
  - `get_options` accepts every choice role.
- [x] 2.5 `prefill.py` and `attachments/extract.py`: compare against canonical values, output encoded `value` plus `display`, and list options for every choice role.

## 3. Value warnings

- [x] 3.1 `values.value_warnings(layout, config)`.
- [x] 3.2 `FormGuide.register_form(..., config=None)` appends the warnings; `LayoutIn.config` in `server.py`.
- [x] 3.3 `formguide check` prints the resolved field specs, and with `--jsx` (plus optional `--form-config`) checks one form and its sample config.
- [x] 3.4 The demo frontend `registerLayout` sends the initial config.

## 4. Tests

- [x] 4.1 New `tests/test_values.py`:
  - id-only dropdown with `value/label` options under `items`: filled, display, card value, prefill value;
  - `Y`/`N` toggle;
  - day-first date format;
  - numbers as numbers and as strings;
  - multiselect with `ids`;
  - radio;
  - detected option pairs, string lists and id→label objects;
  - codec encode and decode, including a codec that raises;
  - YAML field spec parsing and the misspelt-key error;
  - value warnings via `POST /layouts`.
- [x] 4.2 Update existing tests for numbers as JSON numbers, and run `uv run pytest -q`.

## 5. Docs and specs

- [x] 5.1 `docs/ui-components.md`: a "Your components store values differently? Describe them" section, updated value-format tables, the number change and value warnings.
- [x] 5.2 `docs/configuration.md`: field spec keys and a YAML example.
- [x] 5.3 Small updates to `docs/architecture.md` and `README.md` (configure table, breaking number note).
- [x] 5.4 `docs/architecture-pages.html`: a field spec section on "Build the UI" and a row in the Configuration table. Run `python3 scripts/build_docs_site.py`, then republish the artifact.
- [x] 5.5 Run `openspec validate --all --strict`, `python3 scripts/check_english.py` and the tests.

## Workflow follow-up

- Archive the change with `/opsx:archive` after it is implemented and verified.

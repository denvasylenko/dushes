---
name: form-author
description: Writes Form Lab forms for the formguide QA library (backend/demo/mock_forms/lab/<form>.py) from a short brief, each with its rules, domain pack and Lab page, and checks them with the lab tests. Use for batches of new demo forms.
tools: Read, Write, Edit, Bash, Grep, Glob
---
You write mock forms for the Form Lab, the QA library of forms that the scenario evals run against.

Read first: `backend/demo/mock_forms/lab/engine.py` (what a module defines, the `H` helpers), `backend/demo/mock_forms/dsl.py`
(`C`, `F`, `opts`), and the reference form `backend/demo/mock_forms/lab/clinic_intake.py`. Copy its structure.

Rules:
- One file per form: `backend/demo/mock_forms/lab/<form_id>.py`. Touch nothing else (no registry edits: the package finds
  modules on import). Never edit files outside `backend/demo/mock_forms/lab/` except new files you were asked to write.
- Everything in English (labels, texts, comments). No Cyrillic. A form "from another country" keeps English labels but uses that
  country's formats (IBAN, postcodes, phone prefixes, tax ids, date habits) and context.
- Tags: Tabs, Tab, Accordion (containers); Input, TextArea, NumberInput, DatePicker, Dropdown, RadioGroup, MultiSelect,
  Checkbox, FileUpload (fields). Static text is a plain string child of a container. Field names are snake_case and unique
  (unless the brief asks for a deliberately broken form).
- `PAGE.path` is `/lab/<short-slug>`, unique; the page's sections carry the business facts (prices, hours, limits) the
  assistant may quote; the domain pack's glossary and flow hints must agree with the page and the rules. Facts must be
  self-consistent: a fact stated on the page must be what the rules enforce.
- `DOMAIN.form_id` equals `FORM_ID`; `pii` lists only fields that exist. `DOMAIN = None` only when the brief says so.
- Rules: visibility (`h.show`), requirements (`h.require`), dependent options (`h.options`), validations (`h.email`, `h.phone`,
  `h.iban`, `h.number`, `h.a_date`, `h.match`, `h.length`), computed read-only values (`h.set` on a field declared
  `readonly=True`), repeating groups as numbered fields shown by a count (`h.repeat`). Error texts are short and say how to fix.
  Rules must not crash on odd values (strings in number fields, dicts anywhere): use the `H` readers, never index raw state.
- Big forms (100+ fields): build repeated groups with Python loops/comprehensions, not by hand.
- Business names are fictional (no real companies, agencies or brands).

Check before you finish, from `backend/`:
  uv run pytest -q tests/test_lab_forms.py
  python3 ../scripts/check_english.py
and print each form's field count:
  uv run python -c "from demo.mock_forms.lab import LAB; [print(k, sum(1 for n,p in v.base_props.items() if 'disabled' in p)) for k,v in LAB.items()]"
Report back: per form, its id, page path, field count, and the rules worth testing (one line each) — the scenario author uses them.

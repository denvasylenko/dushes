# Proposal

## Why

The agent hard-codes one value format per field role. A dropdown's value is `{id, name}`, options are `[{id, name}]` under `props.options`, a checkbox is `true`/`false`, a date is an ISO string, and a number goes out as a string. Real component libraries differ. A dropdown may store just `"auto"` or `{value, label}` and keep its choices in `items`; a toggle may store `"Y"`/`"N"`; a date may be `"31.05.1990"`. Today a team with such components either rewrites values on the frontend or gets wrong "filled" and "valid" judgements and card values its form cannot take. A developer integrating a new form also has no place to tell the agent "this is how my components hold values".

## What Changes

- Each field tag in `components.fields` can be described by a **field spec** instead of a bare role. The spec covers:
  - `role`;
  - `value`, the shape a choice is stored in: `option`, `id` or `name` (for multiselect `options`, `ids` or `names`);
  - `option_keys`, which keys of an option hold the id and the label;
  - `options_prop`, the props key that holds the options;
  - `true` and `false`, the stored checkbox values;
  - `format`, the date format (`iso`, a `strftime` pattern, or `epoch_ms`);
  - number `value`, either `number` or `string`;
  - `codec`, an import string of a class with `decode`/`encode` for anything else.

  A bare role string keeps working.
- The agent **reads** form values through the field spec into one internal format, leniently: a choice given as an id, a label or an option object is understood. So "filled", "valid option", the diff and learned dependencies work for any library.
- The agent **writes** values back in the form's own format. The card's `changes[].value` and prefill `values[].value` are what the component stores, ready to send to the form backend. `display` stays human text.
- **Option keys are auto-detected** when not configured. Common pairs are recognised: `id/name`, `value/label`, `key/label`, `value/text`, `code/name`, `code/title`. Options as a list of strings, or as an `{id: label}` object, are recognised too.
- New field roles: `radio`, a single choice that behaves like `select`, and `multiselect`, a list of choices.
- **BREAKING**: a number in a card or prefill value is a JSON number by default (`250000`, not `"250000"`). Set `value: string` on the number field spec to keep strings.
- `POST /agent/layouts` (and `FormGuide.register_form`) accepts an optional `config` and also reports value warnings for it: a value that cannot be read with the configured spec, or options whose keys cannot be found. `formguide check` prints the field specs in use.

## Capabilities

### New Capabilities
- `component-values`: how a field's stored value and options are described per component tag, read into the internal format and written back in the form's own format.

### Modified Capabilities
- `form-layout`: the configurable component map accepts field specs and the new roles `radio` and `multiselect`.
- `field-changes`: "Values are normalized". Card values are written in the form's own format, numbers default to JSON numbers, and multiselect values are validated per item.
- `form-prefill`: prefill values use the same form-format encoding as cards.
- `http-api`: `POST /layouts` accepts an optional `config` and returns value warnings.

## Impact

- Code:
  - `backend/formguide/form/layout.py`: `ComponentMap` and the field spec;
  - new `backend/formguide/form/values.py`: decode, encode and option detection;
  - `form/overlay.py`: `Eff.value`, `Eff.options`, `filled`, `invalid_value`, display and trigger values;
  - `form/render.py`: options and multiselect;
  - `agent/tools.py`: `_norm_value`, `propose_changes`, `get_options`;
  - `prefill.py`, `attachments/extract.py`, `config.py` (YAML parsing), `guide.py` and `server.py` (`register_form` with config), `cli.py` (`check`).
- API: the card `value` and prefill `value` follow the configured format. With default specs they are unchanged, except that numbers are now JSON numbers.
- Demo: the mock form backend already parses numbers from numbers or strings. The demo UI renders the value it gets.
- Docs: `docs/ui-components.md` gains a "Describe your components" section; `docs/configuration.md`, `docs/architecture.md`, `docs/architecture-pages.html` and `README.md` get matching updates.
- No new dependencies.

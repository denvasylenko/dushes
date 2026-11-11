# Design

## Context

All value logic already goes through one place. `Overlay` builds an `Eff` per node from `props[name]` and `state[name]`, and everything downstream reads `Eff.value` and `Eff.options`. That covers filled / needs_input / invalid_value, display and trigger values, the diff and `DepStore`, context rendering, `get_options`, extraction hints and prefill. The writing side is just as narrow: `_norm_value` in `agent/tools.py` turns the model's raw value into the stored value, and `propose_changes` and `suggest_prefill` put it on the card or into the prefill result. The `ComponentMap` in `form/layout.py` maps tag to role string, and `LayoutIndex` stores the role on each `Node`.

## Goals / Non-Goals

**Goals:**
- One internal ("canonical") value per role, independent of the component library, so no reasoning code changes.
- Conversion happens at two edges only: reading the config (decode) and handing a value to the client (encode).
- Existing YAML and code that maps tags to role strings keep working, and default output is unchanged apart from numbers.

**Non-Goals:**
- Renaming the other props (`visible`, `disabled`, `label`, ...), e.g. a library that uses `hidden` or `title`. That would be a later "prop aliases" change; the same field spec can grow a `props` key then.
- Per-field overrides inside one form. Components of the same tag share a shape in practice; a codec can look at `props` for exceptions.
- Repeating groups (lists of sub-forms).

## Decisions

### Canonical values

| Role | Canonical value |
|---|---|
| text | `str` |
| number | `int` or `float` (from a number or a numeric string) |
| date | ISO `str` |
| select, radio | `{id, name}` |
| multiselect | `list[{id, name}]` |
| bool | `bool` |
| file | unchanged |

Options are canonical `[{id, name, raw}]`, where `raw` is the original option. Keeping `raw` lets `value: option` write back exactly what the form gave, extra keys included.

Alternative: store raw values and teach each consumer the spec. Rejected: about 12 call sites would each need it, and they would drift.

### `FieldSpec` and a new `form/values.py`

`FieldSpec` is a frozen dataclass: role, value, option_keys, options_prop, true, false, format, codec. `ComponentMap.fields` accepts `str | dict | FieldSpec`, normalised once in `ComponentMap.__post_init__`. `ComponentMap.spec(tag)` returns the `FieldSpec`. `Node.role` stays a plain string (`radio` keeps its name). Choice logic checks `role in CHOICE = {"select", "radio"}`, so the agent can still tell the user "pick one of the radio buttons".

`values.py` holds:
- `read_options(spec, props) -> (list[Option] | None, warning | None)`;
- `decode(spec, raw, options) -> (canonical, ok)`;
- `encode(spec, canonical, options, props) -> raw`.

Decode is lenient and never raises. If it cannot read a value, it returns `ok=False` and the raw value as text, so a broken value is still "filled" and shown as is.

### Lenient decode, strict encode

Decode accepts any plausible shape: for a choice, a dict with the id key, a scalar id, or a label (case-insensitive). A misconfigured or mixed form is then still understood. Encode follows the spec exactly, because the form backend expects one shape.

### Option-key detection

Option-key detection is used when `option_keys` is not set:
- try the known pairs in order on the first dict option and pick the first pair whose keys exist on all options;
- a list of strings or numbers becomes `id = name = str(x)`;
- a dict that is not a list becomes `[{id: k, name: v}]`.

Detection runs per Overlay (once per turn). It costs about as much as the existing `options_sig` hashing.

### Where encode happens

Encode happens in `_t_propose_changes` and `suggest_prefill`, after `_norm_value` returns canonical. `_norm_value` itself stays canonical-only, so its existing validation messages stay the same. The card change gets `value = encode(...)` and `display` from the canonical value. The pending-changes record (used by `confirm` for `agent_names`) needs only names, so nothing else changes.

### Codecs

A codec is loaded with `import_object`, instantiated once with no arguments, and cached on the `FieldSpec`. Both methods are optional. Exceptions are caught at the edge (see the spec).

### Value warnings

Value warnings come from a function `value_warnings(layout, config)` in `values.py`. It builds the options and decodes each field. `register_form(jsx, form_id, domain, config=None)` appends its output, `LayoutIn` gains `config: dict | None`, and the demo frontend sends the initial config when it registers the layout, so a developer sees the problems in the network tab. `formguide check` prints the component map with resolved field specs.

### Numbers become JSON numbers by default

The decision is in the proposal. Canonical numbers are numbers, so the diff and the display show `250000` either way. `value: string` writes `str(canonical)`, with no exponent and integral floats without `.0`.

## Risks / Trade-offs

- [Lenient decode hides a misconfiguration] → value warnings at registration, and the context marks an unreadable value with ⚠ so the model mentions it.
- [Label matching picks the wrong option when two options share a label] → id matches win over label matches; duplicates are rare and the card shows the result for the user to check.
- [Breaking number output for current integrators] → called out in the proposal and README; `value: string` restores the old behaviour.
- [Codec instantiation side effects] → instantiated once, on first use, not at import.

## Migration Plan

No data migration. Learned dependency files store trigger values as `"<id>|<name>"`, built from canonical values. Those are unchanged for default specs, so existing `deps/` files stay valid. To roll back, revert the change; YAML with field spec objects would then fail to load, so keep role strings in shared configs until this is released.

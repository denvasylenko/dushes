"""Field values: the form's own format <-> one internal format per role.

Every component library stores values its own way: a dropdown may hold an option
object, just its id or its label; options may be `[{id, name}]`, `[{value, label}]`
or plain strings; a checkbox may hold "Y"/"N"; a date "31.05.1990". The field spec
(layout.FieldSpec, configured per tag in `components.fields`) says which.

The agent reasons only about canonical values:

    text         str
    number       int | float
    date         "YYYY-MM-DD"
    select/radio {"id", "name"}
    multiselect  [{"id", "name"}, ...]
    bool         True | False
    file         unchanged

`decode` reads a stored value leniently (any plausible shape) and never raises;
`encode` writes a canonical value strictly in the configured shape.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Any

from .layout import CHOICE, FieldSpec, LayoutIndex

# id/label key pairs of option objects in common UI kits, tried in this order
OPTION_KEY_PAIRS = (("id", "name"), ("value", "label"), ("key", "label"), ("value", "text"),
                    ("code", "name"), ("code", "title"), ("id", "label"), ("value", "name"), ("key", "value"))

# Yes / no in several languages; Cyrillic words are escaped: \u0434\u0430 = "da" (ru), \u0442\u0430\u043a = "tak" (uk),
# \u043d\u0435\u0442 = "net" (ru), \u043d\u0456 = "ni" (uk).
TRUE_WORDS = {"true", "1", "yes", "y", "on", "\u0434\u0430", "\u0442\u0430\u043a", "ja", "oui", "si", "s\u00ed"}
FALSE_WORDS = {"false", "0", "no", "n", "off", "\u043d\u0435\u0442", "\u043d\u0456", "nein", "non"}

Option = dict  # {"id": original id, "name": label text, "raw": the option as the form gave it}


class CodecError(ValueError):
    pass


# ---------------------------------------------------------------- options


def detect_keys(items: list[dict]) -> tuple[str, str] | None:
    for k_id, k_name in OPTION_KEY_PAIRS:
        if all(k_id in o and k_name in o for o in items):
            return k_id, k_name
    return None


def read_options(spec: FieldSpec | None, props: dict[str, Any]) -> tuple[list[Option] | None, str | None]:
    """The field's options as [{id, name, raw}] plus a warning when their keys cannot be found."""
    prop = spec.options_prop if spec else "options"
    raw = props.get(prop)
    if raw is None:
        return None, None
    if isinstance(raw, dict):   # {id: label}
        return [{"id": k, "name": str(v), "raw": k} for k, v in raw.items()], None
    if not isinstance(raw, list):
        return None, f"props.{prop} is not a list"
    dicts = [o for o in raw if isinstance(o, dict)]
    keys = spec.option_keys if spec and spec.option_keys else (detect_keys(dicts) if dicts else None)
    warning = None
    if dicts and (not keys or not all(keys[0] in o and keys[1] in o for o in dicts)):
        warning = (f"the option objects in props.{prop} have no recognisable id/label keys "
                   f"(e.g. {json.dumps(dicts[0], ensure_ascii=False, default=str)[:80]}); set option_keys")
        keys = None
    out: list[Option] = []
    for o in raw:
        if isinstance(o, dict):
            if keys:
                out.append({"id": o[keys[0]], "name": str(o[keys[1]]), "raw": o})
            else:
                text = json.dumps(o, ensure_ascii=False, default=str)
                out.append({"id": text, "name": text, "raw": o})
        else:
            out.append({"id": o, "name": str(o), "raw": o})
    return out, warning


def find_option(options: list[Option] | None, value: Any, keys: tuple[str, str] | None = None) -> Option | None:
    """An option by object, id (preferred) or label (case-insensitive)."""
    if not options or value is None:
        return None
    if isinstance(value, dict):
        for k in ([keys[0]] if keys else []) + [p[0] for p in OPTION_KEY_PAIRS]:
            if k in value:
                found = find_option(options, value[k])
                if found:
                    return found
        return None
    s = str(value).strip()
    for o in options:
        if str(o["id"]) == s:
            return o
    low = s.casefold()
    for o in options:
        if str(o["id"]).casefold() == low or o["name"].strip().casefold() == low:
            return o
    return None


def _choice_of(o: Option) -> dict:
    return {"id": o["id"], "name": o["name"]}


# ---------------------------------------------------------------- codecs

_CODECS: dict[str, Any] = {}


def _codec(spec: FieldSpec | None) -> Any:
    if not spec or not spec.codec:
        return None
    if spec.codec not in _CODECS:
        from ..skills import import_object
        _CODECS[spec.codec] = import_object(spec.codec)()
    return _CODECS[spec.codec]


# ---------------------------------------------------------------- numbers / dates


def parse_number(value: Any) -> int | float:
    if isinstance(value, bool):
        raise ValueError("not a number")
    if isinstance(value, (int, float)):
        f = float(value)
    else:
        s = re.sub(r"[\s_ ]", "", str(value)).replace(",", ".")
        f = float(s)
    return int(f) if f.is_integer() and abs(f) < 1e15 else f


def _number_text(n: int | float) -> str:
    return str(int(n)) if float(n).is_integer() and abs(n) < 1e15 else repr(float(n))


def parse_date(value: Any, fmt: str = "iso") -> str:
    """-> "YYYY-MM-DD". Tries the configured format, then ISO, then DD.MM.YYYY."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if fmt == "epoch_ms":
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
        raise ValueError("a number is not a date")
    s = str(value).strip()
    pats = ([fmt] if fmt not in ("iso", "epoch_ms") else []) + ["%Y-%m-%d", "%d.%m.%Y"]
    for p in pats:
        try:
            return datetime.strptime(s, p).date().isoformat()
        except ValueError:
            pass
    try:
        return date.fromisoformat(s[:10]).isoformat()   # "1990-05-31T00:00:00Z"
    except ValueError:
        pass
    if fmt == "epoch_ms" and s.isdigit():
        return parse_date(int(s), fmt)
    raise ValueError(f"not a date: {s!r}")


def _bool_of(spec: FieldSpec | None, raw: Any) -> bool | None:
    if spec is not None and not isinstance(spec.true, bool) and raw == spec.true:
        return True
    if spec is not None and not isinstance(spec.false, bool) and raw == spec.false:
        return False
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)) and raw in (0, 1):
        return bool(raw)
    s = str(raw).strip().casefold()
    if s in TRUE_WORDS:
        return True
    if s in FALSE_WORDS:
        return False
    return None


def _split_list(raw: Any) -> list:
    if isinstance(raw, (list, tuple)):
        return list(raw)
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    return [raw]


# ---------------------------------------------------------------- decode / encode


def decode(spec: FieldSpec | None, role: str, raw: Any, options: list[Option] | None,
           props: dict[str, Any] | None = None) -> tuple[Any, bool]:
    """Stored value -> (canonical value, readable). Never raises."""
    codec = _codec(spec)
    if codec is not None and hasattr(codec, "decode"):
        try:
            return codec.decode(raw, props or {}), True
        except Exception:   # noqa: BLE001 - a broken codec must not break the turn
            return (raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False, default=str)), False
    if raw is None:
        return None, True
    if role in ("text", "file", "unknown"):
        return raw, True
    if isinstance(raw, str) and not raw.strip():
        return ([] if role == "multiselect" else None), True
    keys = spec.option_keys if spec else None
    try:
        if role == "number":
            return parse_number(raw), True
        if role == "date":
            return parse_date(raw, spec.format if spec else "iso"), True
        if role == "bool":
            b = _bool_of(spec, raw)
            return (b, True) if b is not None else (bool(raw), False)
        if role in CHOICE:
            return _decode_choice(raw, options, keys), True
        if role == "multiselect":
            return [_decode_choice(x, options, keys) for x in _split_list(raw)], True
    except (ValueError, TypeError, OverflowError):
        return (raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False, default=str)), False
    return raw, True


def _decode_choice(raw: Any, options: list[Option] | None, keys: tuple[str, str] | None) -> dict:
    o = find_option(options, raw, keys)
    if o:
        return _choice_of(o)
    if isinstance(raw, dict):   # a choice that is no longer among the options
        k = keys or detect_keys([raw])
        if k:
            return {"id": raw[k[0]], "name": str(raw[k[1]])}
        raise ValueError("an option object without id/label keys")
    return {"id": raw, "name": str(raw)}


def encode(spec: FieldSpec | None, role: str, value: Any, options: list[Option] | None,
           props: dict[str, Any] | None = None) -> Any:
    """Canonical value -> the form's own format. Raises CodecError if a codec fails."""
    codec = _codec(spec)
    if codec is not None and hasattr(codec, "encode"):
        try:
            return codec.encode(value, props or {})
        except Exception as e:   # noqa: BLE001
            raise CodecError(f"the field's codec could not write {value!r}: {e}") from None
    if value is None:
        return None
    shape = spec.shape if spec else None
    if role in CHOICE:
        return _encode_choice(value, options, shape or "option")
    if role == "multiselect":
        one = {"options": "option", "ids": "id", "names": "name"}[shape or "options"]
        return [_encode_choice(v, options, one) for v in value]
    if role == "bool":
        return (spec.true if spec else True) if value else (spec.false if spec else False)
    if role == "date":
        fmt = spec.format if spec else "iso"
        if fmt == "iso":
            return value
        d = date.fromisoformat(value)
        if fmt == "epoch_ms":
            return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
        return d.strftime(fmt)
    if role == "number":
        return _number_text(value) if shape == "string" else value
    return value


def _encode_choice(value: dict, options: list[Option] | None, shape: str) -> Any:
    o = find_option(options, value)
    if shape == "id":
        return o["id"] if o else value["id"]
    if shape == "name":
        return o["name"] if o else value["name"]
    return o["raw"] if o else {"id": value["id"], "name": value["name"]}


def display(value: Any) -> str:
    """A canonical value as text for people (card rows, prefill)."""
    if isinstance(value, list):
        return ", ".join(display(v) for v in value)
    if isinstance(value, dict):
        return str(value.get("name", value.get("id", "")))
    if value is True:
        return "✓"
    if value is False:
        return "✗"
    if isinstance(value, float) or isinstance(value, int):
        return _number_text(value)
    return str(value)


# ---------------------------------------------------------------- warnings


def value_warnings(layout: LayoutIndex, config: dict[str, Any]) -> list[str]:
    """Problems reading a sample config with the configured field specs, with what to set."""
    props_all = config.get("props") or {}
    state = config.get("state") or {}
    out: list[str] = []
    for n in layout.fields():
        spec = layout.components.spec(n.tag)
        props = props_all.get(n.name) or {}
        role = n.role
        if role in CHOICE or role == "multiselect":
            opts, warn = read_options(spec, props)
            if warn:
                out.append(f"{n.name} <{n.tag}>: {warn}")
            elif opts is None and n.name in props_all:
                prop = spec.options_prop if spec else "options"
                out.append(f"{n.name} <{n.tag}>: no props.{prop}; if the options are under another key, "
                           f"set options_prop")
        else:
            opts = None
        raw = state.get(n.name)
        if raw is None or raw == "" or raw == []:
            continue
        value, ok = decode(spec, role, raw, opts, props)
        shown = json.dumps(raw, ensure_ascii=False, default=str)[:60]
        if not ok:
            hint = {"date": "set format (a strftime pattern or epoch_ms)", "bool": "set true / false",
                    "number": "use a number or a numeric string"}.get(role, "check the field spec")
            out.append(f"{n.name} <{n.tag}>: cannot read the value {shown} as {role}; {hint}")
        elif (role in CHOICE or role == "multiselect") and opts is not None:
            items = value if isinstance(value, list) else [value]
            if any(find_option(opts, v) is None for v in items):
                out.append(f"{n.name} <{n.tag}>: the value {shown} matches no option; if the component stores "
                           f"an id or a label, set value: id / name (multiselect: ids / names)")
    return out

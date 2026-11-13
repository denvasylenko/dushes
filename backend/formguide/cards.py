"""Cards from blocks: cards of your own, laid out by the developer and filled by the model.

A card spec in formguide.yaml (or `GuideConfig.cards`):

    cards:
      - type: barber_match
        description: Ask whether the barber we found is the one the user means.
        wait: true                                   # a question: the turn waits for the answer
        data:                                        # what the model fills: name -> type ("?" = optional)
          name: string
          shop: string
          rating: number?
          photo: string?
        blocks:                                      # the layout, from the widget's blocks; {name} = a data value
          - {type: title, text: Is this your barber?}
          - {type: place, title: "{name}", subtitle: "{shop}", image: "{photo}", rating: "{rating}", if: name}
          - {type: buttons, items: [{id: yes, label: "Yes, book {name}", style: primary}, {id: no, label: Another barber}]}

Each spec becomes a tool `show_<type>`. Its arguments are checked against `data`, the blocks are filled (a value
that is only a placeholder keeps its type: a list, a number) and the card goes out: an interrupt for `wait: true`
(the answer comes back to the model as text), else a display card (CUSTOM `card`) while the turn goes on.
The widget draws it with its blocks (packages/agui-chat/src/formguide/blocks.ts), so every card looks the same.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

BLOCKS = frozenset({"title", "text", "note", "row", "image", "place", "stat", "diff", "steps", "progress",
                    "swatches", "choice", "field", "buttons", "links", "divider", "hours", "preview"})
TYPES = {"string": "string", "number": "number", "integer": "integer", "boolean": "boolean",
         "string[]": "array", "object[]": "array", "object": "object"}
_PH = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_NAME = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


@dataclass
class CardSpec:
    type: str
    description: str
    blocks: list[dict]
    data: dict[str, str] = field(default_factory=dict)   # name -> "string" | "number?" | "string[]" | ...
    wait: bool = True

    @property
    def tool(self) -> str:
        return f"show_{self.type}"

    def schema(self) -> dict:
        """The tool's input schema from `data`."""
        props: dict[str, Any] = {}
        required: list[str] = []
        for name, t in self.data.items():
            opt = t.endswith("?")
            base = t.rstrip("?")
            p: dict[str, Any] = {"type": TYPES[base]}
            if base == "string[]":
                p["items"] = {"type": "string"}
            elif base == "object[]":
                p["items"] = {"type": "object"}
            props[name] = p
            if not opt:
                required.append(name)
        return {"type": "object", "properties": props, "required": required}


def _placeholders(v: Any) -> set[str]:
    if isinstance(v, str):
        return set(_PH.findall(v))
    if isinstance(v, dict):
        return set().union(*(_placeholders(x) for x in v.values())) if v else set()
    if isinstance(v, list):
        return set().union(*(_placeholders(x) for x in v)) if v else set()
    return set()


def parse_cards(raw: Any) -> list[CardSpec]:
    """`cards` from YAML or code -> specs; a wrong spec is refused when the config loads."""
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise ValueError("cards must be a list of card specs")
    out: list[CardSpec] = []
    for i, c in enumerate(raw):
        if isinstance(c, CardSpec):
            out.append(c)
            continue
        if not isinstance(c, dict):
            raise ValueError(f"cards[{i}] must be a mapping")
        t = str(c.get("type") or "")
        if not _NAME.match(t):
            raise ValueError(f"cards[{i}].type must be a snake_case name, got {t!r}")
        unknown = set(c) - {"type", "description", "blocks", "data", "wait"}
        if unknown:
            raise ValueError(f"cards.{t}: unknown key(s) {sorted(unknown)}")
        data = c.get("data") or {}
        if not isinstance(data, dict):
            raise ValueError(f"cards.{t}.data must map names to types")
        for k, v in data.items():
            if str(v).rstrip("?") not in TYPES:
                raise ValueError(f"cards.{t}.data.{k}: type must be one of {sorted(TYPES)} (add ? for optional)")
        blocks = c.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            raise ValueError(f"cards.{t}.blocks must be a non-empty list")
        for j, b in enumerate(blocks):
            if not isinstance(b, dict) or b.get("type") not in BLOCKS:
                raise ValueError(f"cards.{t}.blocks[{j}]: unknown block {b.get('type') if isinstance(b, dict) else b!r}; "
                                 f"known: {sorted(BLOCKS)}")
        missing = _placeholders(blocks) - set(data) - {"left"}   # {left}: the steps block counts it itself
        missing |= {str(b["if"]) for b in blocks if b.get("if") and str(b["if"]) not in data}
        if missing:
            raise ValueError(f"cards.{t}: placeholders not in data: {sorted(missing)}")
        desc = str(c.get("description") or "").strip()
        if not desc:
            raise ValueError(f"cards.{t}.description is required (it tells the model when to show the card)")
        out.append(CardSpec(type=t, description=desc, blocks=blocks, data={k: str(v) for k, v in data.items()},
                            wait=bool(c.get("wait", True))))
    names = [c.type for c in out]
    if len(set(names)) != len(names):
        raise ValueError("cards: two specs with the same type")
    return out


def _empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _fill(v: Any, data: dict[str, Any]) -> Any:
    if isinstance(v, str):
        whole = _PH.fullmatch(v)
        if whole and whole.group(1) in data:   # "{items}" keeps a list, "{rating}" a number
            return data[whole.group(1)]
        return _PH.sub(lambda m: "" if _empty(data.get(m.group(1))) else str(data[m.group(1)])
                       if m.group(1) in data else m.group(0), v)
    if isinstance(v, dict):
        return {k: _fill(x, data) for k, x in v.items()}
    if isinstance(v, list):
        return [_fill(x, data) for x in v]
    return v


def check(spec: CardSpec, args: Any) -> dict[str, Any]:
    """The model's arguments, checked against `data` (ValueError with the problem)."""
    a = args if isinstance(args, dict) else {}
    out: dict[str, Any] = {}
    for name, t in spec.data.items():
        base = t.rstrip("?")
        v = a.get(name)
        if _empty(v):
            if not t.endswith("?"):
                raise ValueError(f"{name} is required")
            continue
        ok = {"string": isinstance(v, str), "number": isinstance(v, (int, float)) and not isinstance(v, bool),
              "integer": isinstance(v, int) and not isinstance(v, bool), "boolean": isinstance(v, bool),
              "string[]": isinstance(v, list) and all(isinstance(x, str) for x in v),
              "object[]": isinstance(v, list) and all(isinstance(x, dict) for x in v),
              "object": isinstance(v, dict)}[base]
        if not ok:
            raise ValueError(f"{name} must be {base}")
        out[name] = v[:2000] if isinstance(v, str) else v
    return out


def build(spec: CardSpec, args: Any) -> dict[str, Any]:
    """The card payload the widget draws: {type: blocks, name, blocks}."""
    data = check(spec, args)
    blocks = []
    for b in spec.blocks:
        cond = b.get("if")
        if cond and _empty(data.get(str(cond))):
            continue
        blocks.append(_fill({k: v for k, v in b.items() if k != "if"}, data))
    return {"type": "blocks", "name": spec.type, "blocks": blocks}


def answer_text(spec: CardSpec, resume: dict[str, Any]) -> str:
    """The tool result the model gets for a waiting card."""
    if not isinstance(resume, dict) or resume.get("accepted") is False or not resume.get("action"):
        return f"The user closed the {spec.type} card without answering."
    label = str(resume.get("label") or resume["action"])
    vals = {k: v for k, v in (resume.get("values") or {}).items() if not _empty(v)}
    text = f'The user chose "{label}" ({resume["action"]}) on the {spec.type} card.'
    if vals:
        text += " Values: " + "; ".join(f"{k} = {v}" for k, v in vals.items()) + "."
    return text

"""Layout index: the static structure of a form, parsed from a JSX string.

The JSX is simple: tags, a single `name` attribute and occasional text, so a
small tokenizer is enough. If the JSX ever gains {…} expressions, switch to
tree-sitter-javascript and keep the LayoutIndex interface unchanged.

The index is built once per jsx_hash and cached (it is the same for every user
of the form).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


FIELD_ROLES = ("text", "number", "date", "select", "radio", "multiselect", "bool", "file")
CHOICE = frozenset({"select", "radio"})          # one option out of a list
_VALUE_SHAPES = {"select": ("option", "id", "name"), "radio": ("option", "id", "name"),
                 "multiselect": ("options", "ids", "names"), "number": ("number", "string")}
_DEFAULT_SHAPE = {"select": "option", "radio": "option", "multiselect": "options", "number": "number"}
_SPEC_KEYS = {"role", "value", "option_keys", "options_prop", "true", "false", "format", "codec"}


@dataclass(frozen=True)
class FieldSpec:
    """How one field component stores its value (see "Build the form UI" in the docs site: site/src/content/docs/guides/form-ui.md).

    role          one of FIELD_ROLES
    value         select/radio: option | id | name; multiselect: options | ids | names; number: number | string
    option_keys   {"id": key, "name": key} of an option object; detected when None
    options_prop  the props key holding the options
    true / false  the stored checkbox values (default: JSON booleans)
    format        date: "iso", a strftime pattern, or "epoch_ms"
    codec         "module:Class" with optional decode(raw, props) / encode(value, props)
    """
    role: str
    value: str | None = None
    option_keys: tuple[str, str] | None = None
    options_prop: str = "options"
    true: Any = True
    false: Any = False
    format: str = "iso"
    codec: str | None = None

    @property
    def shape(self) -> str | None:
        return self.value or _DEFAULT_SHAPE.get(self.role)

    @classmethod
    def parse(cls, tag: str, raw: "str | dict | FieldSpec") -> "FieldSpec":
        if isinstance(raw, FieldSpec):
            spec = raw
        elif isinstance(raw, str):
            spec = cls(role=raw)
        elif isinstance(raw, dict):
            # YAML reads the keys `true:` / `false:` as booleans
            raw = {("true" if k is True else "false" if k is False else k): v for k, v in raw.items()}
            unknown = set(raw) - _SPEC_KEYS
            if unknown:
                raise ValueError(f"components.fields.{tag}: unknown key(s) {sorted(map(str, unknown))}; "
                                 f"allowed: {sorted(_SPEC_KEYS)}")
            if "role" not in raw:
                raise ValueError(f"components.fields.{tag}: 'role' is required")
            kw = dict(raw)
            ok = kw.get("option_keys")
            if ok is not None:
                if not isinstance(ok, dict) or set(ok) != {"id", "name"}:
                    raise ValueError(f"components.fields.{tag}: option_keys must be {{id: <key>, name: <key>}}")
                kw["option_keys"] = (str(ok["id"]), str(ok["name"]))
            spec = cls(**kw)
        else:
            raise ValueError(f"components.fields.{tag}: expected a role or a field spec, got {raw!r}")
        if spec.role not in FIELD_ROLES:
            raise ValueError(f"components.fields.{tag}: unknown role {spec.role!r}; allowed: {list(FIELD_ROLES)}")
        if spec.value is not None and spec.value not in _VALUE_SHAPES.get(spec.role, ()):
            allowed = _VALUE_SHAPES.get(spec.role)
            raise ValueError(f"components.fields.{tag}: value {spec.value!r} is not valid for role {spec.role!r}"
                             + (f"; allowed: {list(allowed)}" if allowed else "; this role takes no 'value'"))
        return spec


@dataclass(frozen=True)
class ComponentMap:
    """Your component library: JSX tag -> role. Configured once per library, not per form.

    Container roles: tabs, tab, accordion, section, form, repeat (a list of rows: its children are the template of
    one row, written once). Field roles: FIELD_ROLES.
    A field tag maps to a role string or to a FieldSpec / dict describing how the
    component stores its value. Unknown tags are kept (role "unknown") and reported.
    """
    containers: dict[str, str] = field(default_factory=lambda: {
        "Tabs": "tabs", "Tab": "tab", "Accordion": "accordion", "Section": "section", "Form": "form",
        "Repeat": "repeat"})
    fields: dict[str, Any] = field(default_factory=lambda: {
        "Input": "text", "NumberInput": "number", "TextArea": "text", "DatePicker": "date",
        "Dropdown": "select", "RadioGroup": "radio", "MultiSelect": "multiselect", "Checkbox": "bool",
        "FileUpload": "file"})

    def __post_init__(self) -> None:
        specs = {tag: FieldSpec.parse(tag, raw) for tag, raw in self.fields.items()}
        object.__setattr__(self, "_specs", specs)

    def spec(self, tag: str) -> FieldSpec | None:
        return self._specs.get(tag)  # type: ignore[attr-defined]


DEFAULT_COMPONENTS = ComponentMap()

_TOKEN = re.compile(r"<\s*(/)?\s*([A-Za-z][\w.]*)([^>]*?)(/)?\s*>|([^<]+)", re.S)
_NAME = re.compile(r"""\bname\s*=\s*(?:"([^"]*)"|'([^']*)'|\{\s*["']([^"']*)["']\s*\})""")


@dataclass
class Node:
    addr: str               # "1.2.3": nesting and order from the JSX
    tag: str
    role: str               # tabs/tab/accordion/... | text/number/select/... | "static_text"
    name: str
    parent: str | None
    depth: int
    children: list[str] = field(default_factory=list)
    text: str | None = None
    template: str | None = None   # a row's field: the template field it repeats ("qty" for "items.1.qty")

    @property
    def is_container(self) -> bool:
        return self.role in ("tabs", "tab", "accordion", "section", "form", "container", "repeat", "row")

    @property
    def is_field(self) -> bool:
        return not self.is_container and self.role != "static_text"


class LayoutIndex:
    def __init__(self, jsx: str, components: ComponentMap = DEFAULT_COMPONENTS):
        self.components = components
        self.jsx_hash = jsx_hash(jsx)
        self.nodes: dict[str, Node] = {}
        self.order: list[str] = []
        self.root: str | None = None
        self.warnings: list[str] = []
        self._parse(jsx)
        self._rows: dict[tuple, LayoutIndex] = {}
        self.base = self   # the parsed layout (an expanded one points back to it: its repeats' templates)
        self.repeats = [n for n in self.order if self.nodes[n].role == "repeat"]
        for r in self.repeats:
            if any(d.role == "repeat" for d in self.descendants(r)):
                self.warnings.append(f"a repeat inside the repeat {r} is not supported: its rows are not expanded")

    # ------------------------------------------------------------ parsing
    def _parse(self, jsx: str) -> None:
        stack: list[Node] = []
        counters: list[int] = [0]
        for m in _TOKEN.finditer(jsx):
            closing, tag, attrs, selfclose, text = m.groups()
            if text is not None:
                t = " ".join(text.split())
                if t and stack:
                    self._add(stack, counters, "#text", None, text=t)
                continue
            if closing:
                if not stack or stack[-1].tag != tag:
                    self.warnings.append(f"unbalanced </{tag}>")
                    continue
                stack.pop()
                counters.pop()
                continue
            nm = _NAME.search(attrs or "")
            name = next((g for g in nm.groups() if g), None) if nm else None
            node = self._add(stack, counters, tag, name)
            if not selfclose:
                stack.append(node)
                counters.append(0)
        if stack:
            self.warnings.append(f"unclosed tags: {[n.tag for n in stack]}")

    def _add(self, stack, counters, tag, name, text=None) -> Node:
        counters[-1] += 1
        parent = stack[-1] if stack else None
        addr = f"{parent.addr}.{counters[-1]}" if parent else str(counters[-1])
        if tag == "#text":
            role = "static_text"
        elif tag in self.components.containers:
            role = self.components.containers[tag]
        elif self.components.spec(tag):
            role = self.components.spec(tag).role
        else:
            role = "unknown"
            self.warnings.append(f"unknown tag <{tag}> at {addr}")
        if not name:
            name = f"_{tag.lower().lstrip('#')}_{addr}"
        if name in self.nodes:
            self.warnings.append(f"duplicate name {name} at {addr}")
            name = f"{name}__{addr}"
        node = Node(addr, tag, role, name, parent.name if parent else None,
                    len(stack), text=text)
        self.nodes[name] = node
        self.order.append(name)
        if parent:
            parent.children.append(name)
        else:
            self.root = self.root or name
        return node

    # ------------------------------------------------------------ rows
    def row_count(self, name: str, config: dict[str, Any]) -> int:
        """How many rows the repeat `name` shows: props[name].rows, else the row keys in the config, else
        min_rows, else none."""
        props = config.get("props") or {}
        own = props.get(name) or {}
        n = own.get("rows")
        if isinstance(n, int) and not isinstance(n, bool) and n >= 0:
            return n
        seen = -1
        pre = name + "."
        for key in [*props, *(config.get("state") or {})]:
            if key.startswith(pre):
                head = key[len(pre):].split(".", 1)[0]
                if head.isdigit():
                    seen = max(seen, int(head))
        if seen >= 0:
            return seen + 1
        m = own.get("min_rows")
        return m if isinstance(m, int) and not isinstance(m, bool) and m > 0 else 0

    def for_config(self, config: dict[str, Any]) -> LayoutIndex:
        """This layout with every repeat's template expanded into its rows for this config: row containers
        `items.0` and row fields `items.0.qty`. A layout without repeats is returned as it is."""
        if not self.repeats:
            return self
        counts = tuple(self.row_count(r, config) for r in self.repeats)
        if counts not in self._rows:
            self._rows[counts] = self._expand(dict(zip(self.repeats, counts)))
        return self._rows[counts]

    def _expand(self, counts: dict[str, int]) -> LayoutIndex:
        out = object.__new__(LayoutIndex)
        out.components, out.jsx_hash, out.root = self.components, self.jsx_hash, self.root
        out.nodes, out.order, out.warnings = {}, [], list(self.warnings)
        out._rows, out.repeats, out.base = {}, list(self.repeats), self
        inside = {d.name for r in self.repeats for d in self.descendants(r)}

        def put(node: Node) -> None:
            out.nodes[node.name] = node
            out.order.append(node.name)
            if node.parent and node.parent in out.nodes:
                out.nodes[node.parent].children.append(node.name)

        def clone(src: Node, name: str, addr: str, parent: str, depth: int, prefix: str) -> None:
            put(Node(addr, src.tag, src.role, name, parent, depth, text=src.text,
                     template=src.name if src.is_field else None))
            for k, ch in enumerate(src.children, 1):
                c = self.nodes[ch]
                clone(c, prefix + c.name, f"{addr}.{k}", name, depth + 1, prefix)

        for name in self.order:
            if name in inside:
                continue
            n = self.nodes[name]
            put(Node(n.addr, n.tag, n.role, n.name, n.parent, n.depth, text=n.text))
            if n.role == "repeat" and name in counts:
                for i in range(counts[name]):
                    row = f"{name}.{i}"
                    put(Node(f"{n.addr}.{i + 1}", "Row", "row", row, name, n.depth + 1))
                    for k, ch in enumerate(n.children, 1):
                        c = self.nodes[ch]
                        clone(c, f"{row}.{c.name}", f"{n.addr}.{i + 1}.{k}", row, n.depth + 2, f"{row}.")
        return out

    def template(self, repeat: str) -> list[Node]:
        """The fields of one row of a repeat, as written once in the JSX."""
        return [d for d in self.base.descendants(repeat) if d.is_field]

    def repeat_of(self, name: str) -> tuple[str, int, str] | None:
        """(repeat, row, template field) for a row name like "items.1.qty"; None for any other name."""
        for r in self.repeats:
            pre = r + "."
            if name.startswith(pre):
                head, _, rest = name[len(pre):].partition(".")
                if head.isdigit() and rest:
                    return r, int(head), rest
        return None

    # ------------------------------------------------------------ queries
    def get(self, name: str) -> Node | None:
        return self.nodes.get(name)

    def ancestors(self, name: str) -> list[Node]:
        """From the root down to the direct parent."""
        out = []
        n = self.nodes.get(name)
        while n and n.parent:
            n = self.nodes[n.parent]
            out.append(n)
        return out[::-1]

    def descendants(self, name: str):
        for ch in self.nodes[name].children:
            yield self.nodes[ch]
            yield from self.descendants(ch)

    def fields(self):
        return (self.nodes[n] for n in self.order if self.nodes[n].is_field)

    def nearest_container(self, name: str) -> Node | None:
        n = self.nodes.get(name)
        if n and n.is_container and n.role != "tabs":
            return n
        for a in reversed(self.ancestors(name)):
            if a.role != "tabs":
                return a
        return None


def jsx_hash(jsx: str) -> str:
    return hashlib.sha256(jsx.encode()).hexdigest()[:16]


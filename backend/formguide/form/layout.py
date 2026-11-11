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


@dataclass(frozen=True)
class ComponentMap:
    """Your component library: JSX tag -> role. Configured once per library, not per form.

    Container roles: tabs, tab, accordion, section, form. Field roles: text, number,
    date, select, bool, file. Unknown tags are kept (role "unknown") and reported.
    """
    containers: dict[str, str] = field(default_factory=lambda: {
        "Tabs": "tabs", "Tab": "tab", "Accordion": "accordion", "Section": "section", "Form": "form"})
    fields: dict[str, str] = field(default_factory=lambda: {
        "Input": "text", "NumberInput": "number", "TextArea": "text", "DatePicker": "date",
        "Dropdown": "select", "Checkbox": "bool", "FileUpload": "file"})


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

    @property
    def is_container(self) -> bool:
        return self.role in ("tabs", "tab", "accordion", "section", "form", "container")

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
        elif tag in self.components.fields:
            role = self.components.fields[tag]
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


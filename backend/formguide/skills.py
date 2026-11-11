"""Skills: optional know-how and tools the agent can use for some forms.

A skill is a folder with a SKILL.md:

    ---
    name: gift_cards
    description: Check gift card balances and explain how they are applied.
    forms: [barber_booking]          # or "*" for every form (default)
    tools: [demo.skill_tools:check_gift_card]   # optional import strings of LangChain tools
    ---
    Instructions in markdown...

Only name + description are always in the prompt; the agent loads the full
instructions with `use_skill(name)` when the task calls for it. Skill tools are
bound for the forms the skill applies to. Skills can also be built in code:
Skill(name=..., description=..., instructions=..., tools=[my_tool], forms={"x"}).
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from langchain_core.tools import BaseTool


def import_object(path: str) -> Any:
    """'package.module:attr' -> the object."""
    mod, _, attr = path.partition(":")
    obj = importlib.import_module(mod)
    for part in attr.split(".") if attr else []:
        obj = getattr(obj, part)
    return obj


@dataclass
class Skill:
    name: str
    description: str
    instructions: str = ""
    forms: set[str] = field(default_factory=lambda: {"*"})
    tools: list[BaseTool] = field(default_factory=list)

    def applies_to(self, form_id: str) -> bool:
        return "*" in self.forms or form_id in self.forms

    @classmethod
    def from_file(cls, path: str | Path) -> "Skill":
        text = Path(path).read_text()
        meta: dict[str, Any] = {}
        body = text
        if text.startswith("---"):
            _, front, body = text.split("---", 2)
            meta = yaml.safe_load(front) or {}
        forms = meta.get("forms", "*")
        forms = {forms} if isinstance(forms, str) else set(forms)
        tools = [import_object(t) for t in meta.get("tools") or []]
        return cls(name=str(meta.get("name") or Path(path).parent.name), description=str(meta.get("description", "")),
                   instructions=body.strip(), forms=forms, tools=tools)


class SkillRegistry:
    def __init__(self, skills: list[Skill] | None = None):
        self._skills: dict[str, Skill] = {s.name: s for s in skills or []}

    @classmethod
    def from_dir(cls, directory: str | Path) -> "SkillRegistry":
        d = Path(directory)
        return cls([Skill.from_file(p) for p in sorted(d.glob("*/SKILL.md"))] if d.exists() else [])

    def add(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def for_form(self, form_id: str) -> list[Skill]:
        return [s for s in self._skills.values() if s.applies_to(form_id)]

    def get(self, name: str, form_id: str) -> Skill | None:
        s = self._skills.get(name)
        return s if s and s.applies_to(form_id) else None

    def tools_for(self, form_id: str) -> list[BaseTool]:
        return [t for s in self.for_form(form_id) for t in s.tools]

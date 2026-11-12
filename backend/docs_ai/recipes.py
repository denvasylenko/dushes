"""Answer recipes: how Ask AI shapes the answer to a kind of question.

Each recipe is a Markdown file in `docs_ai/recipes/` (or `DOCS_AI_RECIPES`), edited without code:

    ---
    name: configure-backend
    title: Configure the backend
    when: [configure, yaml, python, backend, ...]   # words or phrases that point to this kind of question
    ---
    The reader wants to set something up on the server.
    - One sentence: ...
    - One show_code with ...

The server picks at most one recipe per question, by the words in it, and adds it to the model's
instructions for that answer. No extra model call: picking is a word match, so it costs nothing.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_DIR = Path(__file__).with_name("recipes")
# when two recipes match equally, the more specific kind wins
PRIORITY = ["troubleshoot", "can-it", "card-look", "how-it-works", "connect-frontend", "configure-backend"]


@dataclass
class Recipe:
    name: str
    title: str
    body: str
    when: list[str] = field(default_factory=list)

    def score(self, text: str) -> int:
        t = f" {text.lower()} "
        hits = 0
        for w in self.when:
            w = w.lower().strip()
            if not w:
                continue
            if " " in w or not w.isalnum():
                hits += w in t
            else:
                hits += bool(re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", t))
        return hits


def parse(text: str, fallback_name: str) -> Recipe:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    meta, body = (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, text)
    when = meta.get("when") or []
    return Recipe(name=str(meta.get("name") or fallback_name), title=str(meta.get("title") or fallback_name),
                  body=body.strip(), when=[str(w) for w in when] if isinstance(when, list) else [])


def load(directory: str | Path | None = None) -> list[Recipe]:
    d = Path(directory or os.environ.get("DOCS_AI_RECIPES") or DEFAULT_DIR)
    if not d.is_dir():
        return []
    return [parse(p.read_text(encoding="utf-8"), p.stem) for p in sorted(d.glob("*.md"))]


def pick(recipes: list[Recipe], question: str) -> Recipe | None:
    """The recipe whose words the question uses most; ties go to the more specific kind; none below one hit."""
    def rank(r: Recipe) -> tuple[int, int]:
        pri = PRIORITY.index(r.name) if r.name in PRIORITY else len(PRIORITY)
        return (-r.score(question), pri)

    best = min(recipes, key=rank, default=None)
    return best if best is not None and best.score(question) > 0 else None


def instructions(recipe: Recipe | None) -> str:
    return f"\n\nHow to answer this question ({recipe.title}):\n{recipe.body}" if recipe else ""

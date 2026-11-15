"""The judge's rubric: how a conversation with the assistant is scored (0 to 10).

One text for every reader that judges conversations with it: the scenario evals (backend/scripts/evals.py) and a
host's own reviews of real conversations. `RUBRIC_VERSION` changes whenever the text does, so scores made with
different versions are never compared by mistake.
"""
from __future__ import annotations

RUBRIC_VERSION = "2026-11-15"

RUBRIC = """Score the assistant from 0 to 10 (10: a person would be fully satisfied). Take points off for:
- truth: a fact about the business (prices, rates, rules, hours, partners) that the site or its documents do not
  give, or a wrong one (up to 5 points);
- the right agent: a question answered by the wrong assistant, or a user sent back and forth (up to 2);
- cards: changes to the form written out as prose instead of shown as a card, or values filled without one (up to 2);
- the goal: the user did not get what they came for, or had to repeat themselves (up to 3);
- brevity and tone: long, repetitive, or in another language than the user's (up to 1).
Name every point you take off with the sentence or step that caused it."""

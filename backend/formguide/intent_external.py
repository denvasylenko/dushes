"""The external chooser's client (demo branch only; the owner's yes for a local demo, 2026-11-17).

The one module that knows the supplier: its address, its request and its answer. Everything else talks to the
`Chooser` contract of formguide.intent. The key comes from the environment (INTENT_API_KEY), put there by the
launcher from the keychain; it is never logged, printed or written.

One call answers several questions, so the layer asks everything it needs about a phrase at once:
    {"model": ..., "state": {"line": phrase, "screen_now": ..., "language": ...},
     "questions": {name: {"type": "choice", "criteria": {id: label}} | {"type": "noul", "instructions": text}}}
    -> {"answers": {name: {"type": "choice", "choice": id, "confidence": p} | {"type": "noul", "noul": p}}}
"""
from __future__ import annotations

import os
import time
from typing import Any

from .intent import Pick, Question

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
USD_PER_INPUT_TOKEN = 0.042 / 1e6
NONE = "none"   # the option added to every choice: nothing named


class ExternalChooser:
    by = "external"

    def __init__(self, key: str, timeout: float = 5.0):
        import httpx
        self._http = httpx.AsyncClient(timeout=timeout, headers={"Authorization": f"Bearer {key}",
                                                                 "Content-Type": "application/json"})
        self.calls = 0
        self.usd = 0.0

    @staticmethod
    def _wire(q: Question) -> dict[str, Any]:
        if q.kind == "noul":
            return {"type": "noul", "instructions": q.text}
        return {"type": "choice", "instructions": q.text,
                "criteria": {**{o.id: o.label for o in q.options}, NONE: "nothing of these is named"}}

    @staticmethod
    def _pick(q: Question, a: dict[str, Any] | None, ms: int) -> Pick:
        if not isinstance(a, dict):
            return Pick(None, 0.0, ms, "external")
        if q.kind == "noul":
            p = float(a.get("noul") or 0.0)
            return Pick("yes" if p >= 0.5 else "no", p if p >= 0.5 else 1 - p, ms, "external")
        choice = a.get("choice")
        return Pick(None if choice in (None, NONE) else str(choice), float(a.get("confidence") or 0.0), ms, "external")

    async def choose_many(self, phrase: str, language: str, questions: dict[str, Question], screen: str,
                          context: dict[str, Any] | None = None) -> dict[str, Pick]:
        started = time.monotonic()
        sent = {"model": MODEL,
                "state": {"line": phrase, "screen_now": screen, "language": language,
                          "today": time.strftime("%A %d %B"), **(context or {})},
                "questions": {name: self._wire(q) for name, q in questions.items()}}
        r = await self._http.post(URL, json=sent)
        r.raise_for_status()
        body = r.json()
        ms = round((time.monotonic() - started) * 1000)
        sample = os.environ.get("INTENT_SAMPLE", "")
        if sample:   # the demo only: the body as it left and the answer, one JSON line a call; never the key or a header
            import json
            with open(sample, "a", encoding="utf-8") as f:
                f.write(json.dumps({"request": sent, "response": body, "ms": ms}, ensure_ascii=False) + "\n")
        self.calls += 1
        self.tokens = int((body.get("usage") or {}).get("input_tokens") or 0)   # of the last call, for the log
        self.usd += self.tokens * USD_PER_INPUT_TOKEN
        answers = body.get("answers") or {}
        return {name: self._pick(q, answers.get(name), ms) for name, q in questions.items()}

    async def rank(self, phrase: str, language: str, question: Question, screen: str) -> list[tuple[str, float]]:
        """The options of one choice in order, with the supplier's probability of each (its "none" left out)."""
        r = await self._http.post(URL, json={"model": MODEL,
                                             "state": {"line": phrase, "screen_now": screen, "language": language},
                                             "questions": {"q": self._wire(question)}})
        r.raise_for_status()
        body = r.json()
        self.calls += 1
        self.usd += int((body.get("usage") or {}).get("input_tokens") or 0) * USD_PER_INPUT_TOKEN
        probs = ((body.get("answers") or {}).get("q") or {}).get("probabilities") or {}
        return sorted(((str(i), float(p)) for i, p in probs.items() if i != NONE), key=lambda t: -t[1])

    async def choose(self, phrase: str, language: str, question: Question, screen: str) -> Pick:
        return (await self.choose_many(phrase, language, {"q": question}, screen))["q"]


def from_env() -> ExternalChooser | None:
    key = os.environ.get("INTENT_API_KEY", "").strip()
    return ExternalChooser(key) if key else None

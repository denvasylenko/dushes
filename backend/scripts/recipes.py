"""Recipe evals: each docs recipe (backend/demo/recipes/<name>/) runs its own files, and a scenario counts the runs in
which the agent called the recipe's tool. The number goes on the recipe's page ("9 of 10 runs called use_skill").

    uv run python scripts/recipes.py                      # every scenario in evals/recipes/, each --runs times
    uv run python scripts/recipes.py recipe_gift_card_skill --runs 10
    uv run python scripts/recipes.py --offline            # scripted model: the plumbing only, no keys

A recipe folder holds the files its docs page shows: formguide.yaml (always), and skills/, site.yaml, *_tools.py as
the recipe needs. The runner builds the recipe's own app in-process (the folder is put on sys.path, so a tool is
named "gift_card_tools:check_gift_card"), with this runner's data dir, the demo's mock form backend and, when the
folder has a site.yaml, Dushes over it. No demo server is used or restarted.

A scenario (evals/recipes/<name>.yaml):

    name: recipe_gift_card_skill
    recipe: gift-card-skill           # the folder under demo/recipes/
    form: barber_booking              # the form the chat is on (the demo's mock forms)
    page: /book                       # instead of form: a page of the recipe's site.yaml (the visit goes through Dushes)
    runs: 10                          # default runs (--runs overrides)
    card: accept                      # accept | reject | confirm_no (accepts changes, closes confirmations)
    answer: next Tuesday              # typed on a question with no options (a date picker); empty: the question is closed
    turns:                            # the user's messages, scripted (no user model)
      - say: I have a gift card GC-1234-5678. How much is on it?
      - {prefill: {data: {client_name: Ann}}}         # forwardedProps.prefill, no text
      - {say: Here is my payslip, attach: employment_letter.png}
    client_tools:                     # browser tools sent with every run; a call is answered with `result`
      - {name: get_user_locale, description: ..., parameters: {type: object, properties: {}}, result: '{"locale": "de-DE"}'}
    documents: [loan_application/tariffs_2026.md]     # sample documents (demo/samples/kb) added to the form first
    expect:
      tools: [use_skill, check_gift_card]   # all called in a run
      order: true                           # ... in this order
      never_tools: [use_skill]              # none of these called (a negative case)
      tool_args: {use_skill: {name: gift_cards}}   # a call of this tool with these arguments
      executed: {submit_request: false}     # the tool ran (true) or never ran (false): a result that is not an error
      cards: [confirm]                      # card kinds shown: set_fields, ask, confirm, upload, review, blocks
    transcribe: {file: hello.wav, words: [haircut, tuesday]}   # instead of turns: POST /agent/transcribe

A run is a hit when every `expect` condition holds. The report goes to scripts/runs/recipes-<time>.json, and
site/src/data/recipes.json gets {recipe: {runs, hits, scenarios, tool, model, date, report}}: runs and hits are
summed over the recipe's scenarios (2 scenarios x 10 runs = 20 runs).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).parent))
from harness_client import RUNS, SAMPLES, Visit, events  # noqa: E402

RECIPES = HERE / "demo" / "recipes"
SCENARIOS = HERE / "evals" / "recipes"
SITE_DATA = HERE.parent / "site" / "src" / "data" / "recipes.json"
KEYS = {"name", "recipe", "form", "page", "runs", "card", "turns", "client_tools", "documents", "expect", "transcribe", "tags", "answer"}
EXPECT_KEYS = {"tools", "order", "never_tools", "tool_args", "executed", "cards"}


class RecipeError(ValueError):
    pass


@dataclass
class RecipeScenario:
    name: str
    recipe: str
    form: str | None = None
    page: str | None = None
    runs: int = 5
    card: str = "accept"
    turns: list[dict] = field(default_factory=list)
    client_tools: list[dict] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    expect: dict = field(default_factory=dict)
    transcribe: dict | None = None
    tags: list[str] = field(default_factory=list)
    answer: str = ""          # what the user types on a question with no options (a date, a name); empty: closes it

    @property
    def tool(self) -> str:
        e = self.expect
        return ", ".join(e.get("tools") or list(e.get("tool_args") or {}) or
                         [f"not {t}" for t in e.get("never_tools") or []]) or ("transcribe" if self.transcribe else "")


def load(path: Path) -> RecipeScenario:
    raw = yaml.safe_load(path.read_text()) or {}
    bad = sorted(set(raw) - KEYS) or sorted(set(raw.get("expect") or {}) - EXPECT_KEYS)
    if bad:
        raise RecipeError(f"{path.name}: unknown key {bad[0]}")
    for k in ("name", "recipe"):
        if not raw.get(k):
            raise RecipeError(f"{path.name}: {k} is required")
    if not (RECIPES / raw["recipe"] / "formguide.yaml").exists():
        raise RecipeError(f"{path.name}: no recipe folder demo/recipes/{raw['recipe']} with a formguide.yaml")
    if not raw.get("turns") and not raw.get("transcribe"):
        raise RecipeError(f"{path.name}: turns or transcribe is required")
    if raw.get("card", "accept") not in ("accept", "reject", "confirm_no"):
        raise RecipeError(f"{path.name}: card takes accept, reject or confirm_no")
    turns = [{"say": t} if isinstance(t, str) else dict(t) for t in raw.get("turns") or []]
    for t in turns:
        if set(t) - {"say", "prefill", "attach"}:
            raise RecipeError(f"{path.name}: a turn takes say, prefill and attach")
    return RecipeScenario(name=str(raw["name"]), recipe=str(raw["recipe"]), form=raw.get("form"), page=raw.get("page"),
                          runs=int(raw.get("runs", 5)), card=str(raw.get("card", "accept")), turns=turns,
                          client_tools=list(raw.get("client_tools") or []), documents=list(raw.get("documents") or []),
                          expect=dict(raw.get("expect") or {}), transcribe=raw.get("transcribe"),
                          tags=[str(x) for x in raw.get("tags") or []], answer=str(raw.get("answer") or ""))


def load_all(names: list[str] | None = None, folder: Path = SCENARIOS) -> list[RecipeScenario]:
    found = [load(p) for p in sorted(folder.glob("*.yaml"))]
    if names:
        missing = set(names) - {s.name for s in found}
        if missing:
            raise RecipeError(f"no recipe scenario named {sorted(missing)[0]}")
        found = [s for s in found if s.name in names]
    return found


# ===================================================================== the recipe's own app


class OneLine:
    """The offline model: answers in one line, calls no tool (the plumbing only)."""

    @staticmethod
    def make() -> Any:
        from langchain_core.language_models import BaseChatModel
        from langchain_core.messages import AIMessage, AIMessageChunk
        from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

        class _M(BaseChatModel):
            @property
            def _llm_type(self) -> str:
                return "offline"

            def bind_tools(self, tools, **kwargs):  # type: ignore[override]
                return self

            def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Offline answer."))])

            def _stream(self, messages, stop=None, run_manager=None, **kwargs):
                yield ChatGenerationChunk(message=AIMessageChunk(content="Offline answer."))
        return _M()


def model_name(m: Any) -> str:
    for attr in ("model", "model_name", "deployment_name"):
        v = getattr(m, attr, None)
        if isinstance(v, str) and v:
            return v
    return type(m).__name__


def build_app(recipe: str, data_dir: Path, offline: bool = False):
    """The recipe's formguide.yaml as an app: /agent, the demo's mock form backend (/java) and Dushes at /site
    when the folder has a site.yaml. Returns (TestClient, guide)."""
    from fastapi import APIRouter
    from fastapi.testclient import TestClient

    from demo.mock_forms import FORMS
    from formguide import FormGuide, KnowledgeBase, Models
    from formguide.app import create_app
    from formguide.config import load_config
    from formguide.site import Dushes, SiteMap, create_dushes_router
    from formguide.transcript import MemoryTranscriptStore

    folder = RECIPES / recipe
    if str(folder) not in sys.path:   # a recipe's tools: "gift_card_tools:check_gift_card"
        sys.path.insert(0, str(folder))
    cfg = load_config(folder / "formguide.yaml")
    cfg.data_dir = data_dir                      # the runner's data, not the recipe's
    cfg.knowledge = KnowledgeBase(data_dir / "kb", index=getattr(cfg.knowledge, "index", None), scopes=cfg.knowledge.scopes)
    cfg.checkpointer, cfg.transcripts = None, MemoryTranscriptStore()
    if offline:
        cfg.models = Models(agent=OneLine.make())
    guide = FormGuide(cfg)
    app = create_app(guide, prefix="/agent")
    java = APIRouter(prefix="/java")

    @java.get("/form")
    def form(form_id: str) -> dict:
        f = FORMS[form_id]
        return {"form_id": f.form_id, "jsx": f.jsx, "config": f.compute(None), "domain": f.domain}

    @java.post("/event")
    def event(body: dict) -> dict:
        return FORMS[body["form_id"]].compute({**body["state"], **(body.get("changes") or {})})

    app.include_router(java)
    if (folder / "site.yaml").exists():
        def form_for(form_id: str, ctx) -> dict | None:
            f = FORMS.get(form_id)
            if not f:
                return None
            reg = guide.register_form(f.jsx, f.form_id, f.domain)
            return {"config": f.compute(None), "jsx_hash": reg["jsx_hash"], "form_id": f.form_id,
                    "ui": {"activeTabs": {}, "openAccordions": [], "focused": None}}
        site = Dushes(guide, SiteMap.load(folder / "site.yaml"), form_for=form_for)
        app.include_router(create_dushes_router(site), prefix="/site")
    return TestClient(app), guide


# ===================================================================== a chat on one form (/agent/run)


class FormChat:
    """The widget on one form: cards are accepted (or rejected), questions answered with their first option, browser
    tools answered with the scenario's result. Records every tool call (name, args) and every tool result."""

    def __init__(self, http, form_id: str, card: str = "accept", client_tools: list[dict] | None = None, answer: str = ""):
        from demo.mock_forms import FORMS
        self.http, self.form, self.card, self.answer = http, FORMS[form_id], card, answer
        self.config = self.form.compute(None)
        self.hash = http.post("/agent/layouts", json={"jsx": self.form.jsx, "form_id": form_id,
                                                      "domain": self.form.domain}).json()["jsx_hash"]
        self.thread = str(uuid.uuid4())
        self.ui = {"activeTabs": {}, "openAccordions": [], "focused": None, "now": datetime.now().strftime("%Y-%m-%d %A %H:%M")}
        self.client = {t["name"]: t for t in client_tools or []}
        self.calls: list[tuple[str, dict]] = []
        self.results: dict[str, list[str]] = {}   # tool name -> its result texts
        self.log: list[str] = []
        self.attachments: list[dict] = []
        self.cards: list[str] = []                 # the kinds of cards shown

    def _state(self) -> dict:
        s = {"config": self.config, "jsx_hash": self.hash, "form_id": self.form.form_id, "ui": self.ui}
        if self.attachments:
            s["attachments"], self.attachments = self.attachments, []
        return s

    def _body(self, messages: list[dict], fwd: dict | None = None) -> dict:
        tools = [{"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters") or
                  {"type": "object", "properties": {}}} for t in self.client.values()]
        return {"threadId": self.thread, "runId": str(uuid.uuid4()), "messages": messages, "state": self._state(),
                "tools": tools, "context": [], "forwardedProps": fwd or {}}

    def attach(self, filename: str) -> None:
        p = SAMPLES / "attachments" / filename
        r = self.http.post("/agent/attachments", data={"thread_id": self.thread}, files={"file": (p.name, p.read_bytes())}).json()
        self.attachments.append({"id": r["id"], "filename": r["filename"]})
        self.log.append(f"📎 {filename}")

    def turn(self, say: str | None = None, prefill: dict | None = None) -> None:
        self.log.append(f"\n👤 {say or ''}" + (f" (prefill {json.dumps(prefill, ensure_ascii=False)[:120]})" if prefill else ""))
        msgs = [{"id": str(uuid.uuid4()), "role": "user", "content": say}] if say else []
        self._run(self._body(msgs, {"prefill": prefill} if prefill else None))

    def _run(self, body: dict, depth: int = 0) -> None:
        if depth > 12:
            self.log.append("❌ more than 12 runs in a row")
            return
        texts: dict[str, str] = {}
        calls: dict[str, list] = {}
        interrupt, client_calls = None, []
        for e in events(self.http, "/agent/run", body):
            t, name = e["type"], e.get("name")
            if t == "TEXT_MESSAGE_CONTENT":
                texts[e["messageId"]] = texts.get(e["messageId"], "") + e["delta"]
            elif t == "TEXT_MESSAGE_END" and texts.get(e["messageId"], "").strip():
                self.log.append("🤖 " + texts[e["messageId"]].strip())
            elif t == "TOOL_CALL_START":
                calls[e["toolCallId"]] = [e["toolCallName"], ""]
            elif t == "TOOL_CALL_ARGS" and e["toolCallId"] in calls:
                calls[e["toolCallId"]][1] += e["delta"]
            elif t == "TOOL_CALL_END" and e["toolCallId"] in calls:
                tool, raw = calls[e["toolCallId"]]
                try:
                    args = json.loads(raw or "{}")
                except ValueError:
                    args = {"raw": raw}
                self.calls.append((tool, args))
                self.log.append(f"   ⚙ {tool}({json.dumps(args, ensure_ascii=False)[:120]})")
                if tool in self.client:
                    client_calls.append((e["toolCallId"], tool, raw))
            elif t == "TOOL_CALL_RESULT" and e.get("toolCallId") in calls:
                self.results.setdefault(calls[e["toolCallId"]][0], []).append(str(e.get("content") or ""))
            elif t == "RUN_ERROR":
                self.log.append(f"❌ {e.get('message')}")
            elif name == "on_interrupt":
                interrupt = json.loads(e["value"]) if isinstance(e["value"], str) else e["value"]
        if interrupt:
            self._answer(interrupt, depth)
        elif client_calls:   # the browser runs its tools and sends the results back
            msgs = [{"id": str(uuid.uuid4()), "role": "assistant", "toolCalls": [
                {"id": cid, "type": "function", "function": {"name": n, "arguments": raw or "{}"}} for cid, n, raw in client_calls]}]
            msgs += [{"id": str(uuid.uuid4()), "role": "tool", "toolCallId": cid, "content": str(self.client[n].get("result", "ok"))}
                     for cid, n, _raw in client_calls]
            for cid, n, _raw in client_calls:
                self.results.setdefault(n, []).append(str(self.client[n].get("result", "ok")))
            self._run(self._body(msgs), depth + 1)

    def _resume(self, reply: dict, depth: int) -> None:
        self._run({"threadId": self.thread, "runId": str(uuid.uuid4()), "messages": [], "state": self._state(), "tools": [],
                   "context": [], "forwardedProps": {"command": {"resume": reply}}}, depth + 1)

    def _answer(self, it: dict, depth: int) -> None:
        kind = it.get("type") or ("set_fields" if "changes" in it else "card")
        self.cards.append("set_fields" if "changes" in it else kind)
        if kind == "ask":
            opts = it.get("options") or []
            self.log.append(f"   ❓ {it.get('question')} → {opts[0]['label'] if opts else self.answer or 'closed'}")
            self._resume({"answer": {"ids": [opts[0]["id"]]}} if opts else {"answer": {"text": self.answer}} if self.answer
                         else {"accepted": False}, depth)
        elif "changes" in it:
            ok = self.card in ("accept", "confirm_no")
            self.log.append("   🃏 " + "; ".join(f"{c.get('label')} = {c.get('display')}" for c in it["changes"]) + f" → {'accepted' if ok else 'rejected'}")
            if ok:
                self.config = self.form.compute({**self.config["state"], **{c["name"]: c["value"] for c in it["changes"]}})
            self._resume({"accepted": ok, "config": self.config, "ui": self.ui}, depth)
        else:
            ok = kind == "confirm" and self.card == "accept"
            self.log.append(f"   📋 {kind} card → {'confirmed' if ok else 'closed'}")
            self._resume({"accepted": ok, "config": self.config, "ui": self.ui}, depth)


# ===================================================================== one run, the checks


def _arg_match(args: dict, want: dict) -> bool:
    return all(str(args.get(k, "")).strip().lower() == str(v).strip().lower() for k, v in want.items())


def _ran(results: list[str]) -> bool:
    bad = ("not executed", "a card or question is already waiting", "declined", "cancelled", "error")
    return any(r and not r.lower().startswith(bad) for r in results)


def verdict(sc: RecipeScenario, calls: list[tuple[str, dict]], results: dict[str, list[str]],
            cards: list[str] | None = None) -> list[dict]:
    names = [n for n, _a in calls]
    e, out = sc.expect, []
    for k in e.get("cards") or []:
        out.append({"check": f"shows a {k} card", "ok": k in (cards or [])})
    for t in e.get("tools") or []:
        out.append({"check": f"calls {t}", "ok": t in names})
    if e.get("order") and e.get("tools"):
        it = iter(names)
        out.append({"check": "in order " + " > ".join(e["tools"]), "ok": all(t in it for t in e["tools"])})
    for t in e.get("never_tools") or []:
        out.append({"check": f"never calls {t}", "ok": t not in names})
    for t, want in (e.get("tool_args") or {}).items():
        out.append({"check": f"calls {t}({json.dumps(want)})", "ok": any(n == t and _arg_match(a, want) for n, a in calls)})
    for t, want in (e.get("executed") or {}).items():
        out.append({"check": f"{t} {'ran' if want else 'never ran'}", "ok": _ran(results.get(t, [])) == bool(want)})
    return out


def play(sc: RecipeScenario, http, guide, i: int, offline: bool = False) -> dict:
    if sc.transcribe:
        p = SAMPLES / "audio" / sc.transcribe["file"]
        r = http.post("/agent/transcribe", files={"file": (p.name, p.read_bytes(), "audio/wav")})
        text = (r.json().get("text") if r.status_code == 200 else f"HTTP {r.status_code}") or ""
        checks = [{"check": f"hears {w}", "ok": w.lower() in text.lower()} for w in sc.transcribe.get("words") or []]
        log = [f"🎙 {p.name} → {text}"]
    elif sc.page:
        visit = Visit(http, sc.page, answer=lambda q: {"ids": [q["options"][0]["id"]]} if q.get("options") else None)
        for t in sc.turns:
            if t.get("attach"):
                visit.attach(t["attach"])
            visit.say(t.get("say") or "")
        checks, log = verdict(sc, visit.tools, {}, [c.get("type") for c in visit.cards]), visit.log
    else:
        chat = FormChat(http, sc.form, sc.card, sc.client_tools, sc.answer)
        for t in sc.turns:
            if t.get("attach"):
                chat.attach(t["attach"])
            chat.turn(t.get("say"), t.get("prefill"))
        checks, log = verdict(sc, chat.calls, chat.results, chat.cards), chat.log
    hit = all(c["ok"] for c in checks)
    RUNS.mkdir(exist_ok=True)
    path = RUNS / f"recipe-{sc.name}-r{i + 1}{'-offline' if offline else ''}.txt"   # offline never overwrites live
    path.write_text("\n".join(log) + "\n\nCHECKS:\n" + "\n".join(f"{'✅' if c['ok'] else '❌'} {c['check']}" for c in checks))
    return {"hit": hit, "checks": checks, "transcript": str(path.relative_to(HERE.parent))}


def run(names: list[str] | None = None, *, runs: int | None = None, offline: bool = False, write_site: bool = True,
        folder: Path = SCENARIOS) -> dict:
    scenarios = load_all(names, folder)
    out: dict[str, Any] = {"at": datetime.now().isoformat(timespec="seconds"), "offline": offline, "scenarios": []}
    apps: dict[str, tuple] = {}
    tmp = Path(tempfile.mkdtemp(prefix="formguide-recipes-"))
    for sc in scenarios:
        if sc.recipe not in apps:
            apps[sc.recipe] = build_app(sc.recipe, tmp / sc.recipe, offline)
        http, guide = apps[sc.recipe]
        for d in sc.documents:   # the form's documents, as a manager uploads them
            p = SAMPLES / "kb" / d
            guide.add_document(sc.form or p.parent.name, p.name, p.read_bytes())
        n = runs or sc.runs
        res = []
        for i in range(n):
            print(f"▶ {sc.name} ({i + 1}/{n})", flush=True)
            try:
                res.append(play(sc, http, guide, i, offline))
            except Exception as e:  # noqa: BLE001 — a broken run counts as a miss, the others go on
                res.append({"hit": False, "checks": [{"check": "the run ran", "ok": False, "detail": f"{type(e).__name__}: {e}"}]})
        out["scenarios"].append({"name": sc.name, "recipe": sc.recipe, "tool": sc.tool, "runs": n,
                                 "hits": sum(r["hit"] for r in res), "model": "offline" if offline else model_name(guide.models.agent),
                                 "results": res})
    RUNS.mkdir(exist_ok=True)
    report = RUNS / f"recipes-{datetime.now():%Y%m%d-%H%M%S}.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    for s in out["scenarios"]:
        print(f"{'✅' if s['hits'] == s['runs'] else '⚠️ '} {s['name']:<40} {s['hits']}/{s['runs']}  {s['tool']}")
    print(f"\nreport: {report}")
    if write_site and not offline:
        site_numbers(out, report)
    return out


def site_numbers(report: dict, path: Path, target: Path = SITE_DATA) -> dict:
    """recipes.json for the docs: per recipe the runs and hits of all its scenarios in this report (others kept)."""
    data = json.loads(target.read_text()) if target.exists() else {}
    by: dict[str, dict] = {}
    for s in report["scenarios"]:
        r = by.setdefault(s["recipe"], {"runs": 0, "hits": 0, "scenarios": 0, "tool": [], "model": s["model"]})
        r["scenarios"] += 1
        r["runs"] += s["runs"]
        r["hits"] += s["hits"]
        if s["tool"] and s["tool"] not in r["tool"]:
            r["tool"].append(s["tool"])
    for name, r in by.items():
        data[name] = {"runs": r["runs"], "hits": r["hits"], "scenarios": r["scenarios"], "tool": "; ".join(r["tool"]), "model": r["model"],
                      "date": report["at"][:10], "report": str(path.relative_to(HERE.parent))}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(sorted(data.items())), indent=2) + "\n")
    print(f"site numbers: {target}")
    return data


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Recipe evals: how often each docs recipe's agent calls the right tool.")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--runs", type=int, help="runs per scenario (default: the scenario's own)")
    ap.add_argument("--offline", action="store_true", help="a scripted model: checks the plumbing, no keys")
    ap.add_argument("--no-site", action="store_true", help="do not write site/src/data/recipes.json")
    a = ap.parse_args(argv)
    try:
        out = run(a.names or None, runs=a.runs, offline=a.offline, write_site=not a.no_site)
    except RecipeError as e:
        print(f"recipe scenario error: {e}", file=sys.stderr)
        return 2
    return 0 if all(s["hits"] for s in out["scenarios"]) or a.offline else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

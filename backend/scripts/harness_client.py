"""The HTTP client both harnesses use: it talks to the demo server exactly like the frontend.

- `Session`: one form at /agent/run (chat_harness.py): config and ui, UI directives, cards, the form backend.
- `Visit`: a visit to the demo site at /site/run (evals.py): the page, Dushes' directives and hand-offs, the
  form on a form page, cards and questions, and who answered each message.

Both take an `httpx.Client` (the live server by default; a TestClient for the offline evals).
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

BASE = "http://127.0.0.1:8000"
RUNS = Path(__file__).parent / "runs"
SAMPLES = Path(__file__).resolve().parents[1] / "demo" / "samples"
_KB_READY: set[str] = set()


class Session:
    def __init__(self, name: str, form_id: str, http: httpx.Client | None = None):
        self.name = name
        self.form_id = form_id
        self.http = http or httpx.Client(base_url=BASE, timeout=300)
        f = self.http.get("/java/form", params={"form_id": form_id}).json()
        self.config = f["config"]
        reg = self.http.post("/agent/layouts", json={"jsx": f["jsx"], "form_id": form_id, "domain": f["domain"]}).json()
        self.hash = reg["jsx_hash"]
        self.thread = str(uuid.uuid4())
        self.ui: dict[str, Any] = {"activeTabs": {}, "openAccordions": [], "focused": None,
                                   "now": datetime.now().strftime("%Y-%m-%d %A %H:%M")}
        self.log: list[str] = []
        self.pending: list[dict] | None = None
        self.last_text = ""
        self.cards: list[dict] = []
        self.questions: list[dict] = []
        self.answer: str | None = None   # how to answer a question card: an option label (or text); None = skip
        self.tools: list[tuple[str, Any]] = []
        self.ctx_tokens = 0
        self.to_attach: list[dict] = []

    # ------------------------------------------------------------ form backend
    def set(self, **changes: Any) -> None:
        self.config = self.http.post("/java/event", json={
            "form_id": self.form_id, "state": self.config["state"], "changes": changes}).json()
        self.log.append(f"✏️  user edited: {', '.join(f'{k}={_short(v)}' for k, v in changes.items())}")

    def opt(self, name: str, oid: str) -> dict:
        o = next(x for x in self.config["props"][name]["options"] if x["id"] == oid)
        return {"id": o["id"], "name": o["name"]}

    def open(self, tab: str | None = None, acc: str | None = None, tabs: str = "main", focused: str | None = None):
        if tab:
            self.ui["activeTabs"][tabs] = tab
        if acc and acc not in self.ui["openAccordions"]:
            self.ui["openAccordions"].append(acc)
        self.ui["focused"] = focused
        self.log.append(f"👆 user opened: {tab or ''} {acc or ''} {focused or ''}".rstrip())

    # ------------------------------------------------------------ documents
    def setup_kb(self) -> None:
        """Manager flow: replace the form's documents with the samples and compile them (once per run)."""
        setup_documents(self.http, self.form_id)
        self.log.append("📚 the form has business documents (uploaded + compiled by a manager)")

    def attach(self, filename: str) -> None:
        p = SAMPLES / "attachments" / filename
        r = self.http.post("/agent/attachments", data={"thread_id": self.thread},
                           files={"file": (p.name, p.read_bytes())}).json()
        self.to_attach.append({"id": r["id"], "filename": r["filename"]})
        self.log.append(f"📎 user attached {r['filename']}")

    # ------------------------------------------------------------ agent
    def say(self, text: str, card: str = "accept", answer: str | None = None) -> str:
        """card: accept | reject | ignore — what to do with a confirmation card.
        answer: what to click on a question card (an option label, else typed as text); None = skip."""
        self.answer = answer
        self.log.append(f"\n👤 {text}")
        if self.pending:
            self.log.append("   (previous card ignored)")
            self.pending = None
        state = {**self._state(), "attachments": self.to_attach}
        self.to_attach = []
        body = {"threadId": self.thread, "messages": [{"role": "user", "content": text}], "state": state}
        self._run(body, card)
        return self.last_text

    def _state(self) -> dict:
        return {"config": self.config, "jsx_hash": self.hash, "form_id": self.form_id, "ui": self.ui}

    def _run(self, body: dict, card: str) -> None:
        texts: dict[str, str] = {}
        calls: dict[str, list] = {}
        interrupt = None
        for e in events(self.http, "/agent/run", body):
            t, name = e["type"], e.get("name")
            if t == "TEXT_MESSAGE_CONTENT":
                texts[e["messageId"]] = texts.get(e["messageId"], "") + e["delta"]
            elif t == "TEXT_MESSAGE_END":
                self.log.append("🤖 " + texts[e["messageId"]].strip().replace("\n", "\n   "))
                self.last_text = texts[e["messageId"]]
            elif t == "RUN_ERROR":
                self.log.append(f"❌ {e['message']}")
            elif t == "TOOL_CALL_START":
                calls[e["toolCallId"]] = [e["toolCallName"], ""]
            elif t == "TOOL_CALL_ARGS":
                calls[e["toolCallId"]][1] += e["delta"]
            elif t == "TOOL_CALL_END":
                tool, args = calls[e["toolCallId"]][0], json.loads(calls[e["toolCallId"]][1] or "{}")
                self.tools.append((tool, args))
                self.log.append(f"   ⚙ {tool}({_short(args, 110)})")
            elif name == "agent_note":
                self.log.append(f"   💭 (hidden from the user) {_short(e['value'], 100)}")
            elif name == "agent_context":
                self.ctx_tokens = e["value"]["stats"]["context_tokens"]
            elif name == "run_stats":
                s = e["value"]
                ttft = f"{s['ttft_ms'] / 1000:.1f}s" if s.get("ttft_ms") is not None else "-"
                self.log.append(f"   \u23f1 first token {ttft}, run {s['total_ms'] / 1000:.1f}s, "
                                f"tools {len(s['tools'])}, tokens {s['tokens'].get('input')}/{s['tokens'].get('output')}")
            elif name == "ui_directive":
                d = e["value"]
                for s in d["reveal"]:
                    if s["type"] == "tab":
                        self.ui["activeTabs"][s["tabs"]] = s["tab"]
                    elif s["name"] not in self.ui["openAccordions"]:
                        self.ui["openAccordions"].append(s["name"])
                self.ui["focused"] = d["target"]
                self.log.append(f"   🔦 highlight {d['target']}: \"{d['hint']}\"")
            elif name == "on_interrupt":   # a JSON string (ag-ui-langgraph convention)
                interrupt = json.loads(e["value"]) if isinstance(e["value"], str) else e["value"]
        if interrupt and interrupt.get("type") == "ask":
            self.questions.append(interrupt)
            opts = interrupt.get("options") or []
            hit = next((o for o in opts if self.answer and self.answer.lower() in o["label"].lower()), None)
            reply = ({"answer": {"ids": [hit["id"]]}} if hit else
                     {"answer": {"text": self.answer}} if self.answer else {"accepted": False})
            self.log.append(f"   ❓ question: {interrupt['question']} "
                            f"[{', '.join(o['label'] for o in opts)}] → {hit['label'] if hit else self.answer or 'skip'}")
            self.answer = None
            self._run({"threadId": self.thread, "state": self._state(),
                       "forwardedProps": {"command": {"resume": reply}}}, card)
            return
        if interrupt and "changes" not in interrupt:   # review, upload, confirm: a user who closes it / confirms
            kind = interrupt.get("type") or "card"
            accepted = kind == "confirm" and card == "accept"
            self.cards.append({**interrupt, "changes": []})
            self.log.append(f"   \U0001f4cb {kind} card: {str(interrupt.get('title') or interrupt.get('prompt') or interrupt.get('text') or '')[:80]}"
                            f"  \u2192 {'confirm' if accepted else 'close'}")
            self._run({"threadId": self.thread, "state": self._state(), "forwardedProps": {
                "command": {"resume": {"accepted": accepted, "config": self.config, "ui": self.ui}}}}, card)
            return
        if interrupt:
            ch = interrupt["changes"]
            self.cards.append(interrupt)
            self.log.append("   🃏 card: " + "; ".join(f"{c['label']} = {c['display']}" for c in ch) + f"  → {card}")
            if card == "ignore":
                self.pending = ch
                return
            accepted = card == "accept"
            if accepted:
                self.config = self.http.post("/java/event", json={
                    "form_id": self.form_id, "state": self.config["state"],
                    "changes": {c["name"]: c["value"] for c in ch}}).json()
            self._run({"threadId": self.thread, "state": self._state(), "forwardedProps": {
                "command": {"resume": {"accepted": accepted, "config": self.config, "ui": self.ui}}}}, card)

    def value(self, name: str) -> Any:
        return self.config["state"].get(name)

    def proposed(self, name: str) -> bool:
        return any(ch["name"] == name for card in self.cards for ch in card["changes"])

    def save(self, notes: list[str]) -> str:
        RUNS.mkdir(exist_ok=True)
        text = f"=== {self.name} [{self.form_id}] (context ≈{self.ctx_tokens} tok, thread {self.thread})\n"
        text += "\n".join(self.log)
        if notes:
            text += "\n\nCHECKS:\n" + "\n".join(notes)
        (RUNS / f"{self.name}.txt").write_text(text)
        return text


def _short(v: Any, n: int = 60) -> str:
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n] + "…"


def events(http: httpx.Client, url: str, body: dict) -> Iterator[dict]:
    """The AG-UI events of one run, parsed from the SSE stream."""
    with http.stream("POST", url, json=body) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                yield json.loads(line[6:])


def setup_documents(http: httpx.Client, form: str) -> None:
    """Replace the form's documents with the samples and compile them, once per process."""
    if form in _KB_READY:
        return
    for d in http.get(f"/agent/kb/{form}").json()["documents"]:
        http.delete(f"/agent/kb/{form}/documents/{d['doc_id']}")
    files = [("files", (p.name, p.read_bytes(), "text/markdown")) for p in sorted((SAMPLES / "kb" / form).iterdir())]
    http.post(f"/agent/kb/{form}/documents", files=files)
    f = http.get("/java/form", params={"form_id": form}).json()
    r = http.post(f"/agent/kb/{form}/compile", json={"jsx": f["jsx"], "config": f["config"]}).json()
    print(f"KB {form}: {json.dumps(r, ensure_ascii=False)[:1500]}\n", flush=True)
    _KB_READY.add(form)


# ===================================================================== a visit to the demo site (Dushes)


class Form:
    """A form on a page, as the page keeps it: the form backend's config, the registered layout, the ui."""

    def __init__(self, http: httpx.Client, form_id: str):
        self.http, self.form_id = http, form_id
        f = http.get("/java/form", params={"form_id": form_id}).json()
        self.config = f["config"]
        self.hash = http.post("/agent/layouts", json={"jsx": f["jsx"], "form_id": form_id, "domain": f["domain"]}).json()["jsx_hash"]
        self.ui: dict[str, Any] = {"activeTabs": {}, "openAccordions": [], "focused": None,
                                   "now": datetime.now().strftime("%Y-%m-%d %A %H:%M")}
        self.attachments: list[dict] = []

    def apply(self, changes: dict[str, Any]) -> None:
        self.config = self.http.post("/java/event", json={"form_id": self.form_id, "state": self.config["state"],
                                                          "changes": changes}).json()

    def directive(self, d: dict) -> None:
        for s in d.get("reveal") or []:
            if s["type"] == "tab":
                self.ui["activeTabs"][s["tabs"]] = s["tab"]
            elif s["name"] not in self.ui["openAccordions"]:
                self.ui["openAccordions"].append(s["name"])
        self.ui["focused"] = d.get("target")

    def state(self) -> dict:
        s = {"config": self.config, "jsx_hash": self.hash, "form_id": self.form_id, "ui": self.ui}
        if self.attachments:
            s["attachments"], self.attachments = self.attachments, []
        return s


Answer = Callable[[dict], dict | None]   # a question card -> {"ids": [...]} | {"text": ...} | None (skip)


class Visit:
    """One person on the demo site with one chat, as frontend/src/site/Site.tsx drives it: every run carries the
    page (and its form), navigate directives move the visit, a hand-off runs the form agent once the form is
    open, cards are accepted and applied through the form backend, questions are answered by `answer`."""

    def __init__(self, http: httpx.Client, path: str = "/", answer: Answer | None = None, site: str = "/site"):
        self.http = http
        self.site = site   # where the site's Dushes is mounted: /site (Main Street) or /lab (the Form Lab)
        self.thread = str(uuid.uuid4())
        self.pages = {p["path"]: p for p in http.get(f"{site}/map").json()["pages"]}
        self.answer = answer or (lambda q: None)
        self.path = ""
        self.form: Form | None = None
        self.forms: dict[str, Form] = {}   # every form the visit opened, by id: its last state
        self.log: list[str] = []
        self.cards: list[dict] = []        # every card and question the chat showed: {type, ...}
        self.tools: list[tuple[str, dict]] = []
        self.errors: list[str] = []
        self.messages: list[dict] = []     # the conversation as the server keeps it: {role, content, agent?}
        self.tokens = {"input": 0, "output": 0, "cache_read": 0}   # the assistant's, from the server's run_stats
        self.sources: list[dict] = []      # every source chip shown under an answer
        self.stats: list[dict] = []        # per run: ttft_ms, total_ms, tools, tool_errors, output_tokens, model_ms
        self.replies: list[tuple[str, str]] = []   # (message id, text) of every assistant reply, as the widget keeps them
        self.go(path)

    # ------------------------------------------------------------ the page
    def go(self, path: str) -> None:
        if path == self.path:
            return
        self.path = path if path in self.pages else "/"
        fid = self.pages[self.path].get("form")
        if not fid:
            self.form = None
        elif not self.form or self.form.form_id != fid:
            self.form = self.forms.get(fid) or Form(self.http, fid)
            self.forms[fid] = self.form
        self.log.append(f"🧭 on {self.path}" + (f" (form {fid})" if fid else ""))

    def state(self) -> dict:
        p = self.pages[self.path]
        s: dict[str, Any] = {"page": {"path": self.path, "title": p.get("title", "")}}
        if self.form:
            s["form"] = self.form.state()
        return s

    def attach(self, filename: str) -> None:
        """A file the user attaches to their next message (the chat uploads it under the site thread)."""
        p = SAMPLES / "attachments" / filename
        r = self.http.post("/agent/attachments", data={"thread_id": self.thread}, files={"file": (p.name, p.read_bytes())}).json()
        if self.form:
            self.form.attachments.append({"id": r["id"], "filename": r["filename"]})
        self.log.append(f"📎 attached {r['filename']}")

    # ------------------------------------------------------------ the chat
    def say(self, text: str, reply_to: dict | list | None = None) -> None:
        """reply_to: {message_id, quote} or a list of {message_id, quote, note?}: a reply to quotes the user selected."""
        quotes = reply_to if isinstance(reply_to, list) else [reply_to] if reply_to else []
        self.log.append(f"\n👤 {text}" + "".join(f"  (replying to the quote \"{q.get('quote')}\"" + (f" with the note \"{q['note']}\"" if q.get("note") else "")
                                                + ")" for q in quotes))
        body: dict[str, Any] = {"threadId": self.thread, "messages": [{"role": "user", "content": text}], "state": self.state()}
        if reply_to:
            body["forwardedProps"] = {"reply_to": reply_to}
        self._run(body)

    def _resume(self, reply: dict, depth: int) -> None:
        self._run({"threadId": self.thread, "state": self.state(), "forwardedProps": {"command": {"resume": reply}}}, depth + 1)

    def _run(self, body: dict, depth: int = 0) -> None:
        if depth > 20:   # a chain of question cards answered one after another
            self.errors.append("more than 20 runs in a row without the user")
            return
        texts: dict[str, str] = {}
        calls: dict[str, list] = {}
        interrupt = directive = None
        try:
            for e in events(self.http, f"{self.site}/run", body):
                t, name = e["type"], e.get("name")
                if t == "TEXT_MESSAGE_CONTENT":
                    texts[e["messageId"]] = texts.get(e["messageId"], "") + e["delta"]
                elif t == "TEXT_MESSAGE_END" and texts.get(e["messageId"], "").strip():
                    self.replies.append((e["messageId"], texts[e["messageId"]]))
                    self.log.append("🤖 " + texts[e["messageId"]].strip().replace("\n", "\n   "))
                elif t == "RUN_ERROR":
                    self.errors.append(str(e.get("message")))
                    self.log.append(f"❌ {e.get('message')}")
                elif t == "TOOL_CALL_START":
                    calls[e["toolCallId"]] = [e["toolCallName"], ""]
                elif t == "TOOL_CALL_ARGS":
                    calls[e["toolCallId"]][1] += e["delta"]
                elif t == "TOOL_CALL_END" and e["toolCallId"] in calls:
                    tool, raw = calls[e["toolCallId"]]
                    try:
                        args = json.loads(raw or "{}")
                    except ValueError:
                        args = {"raw": raw}
                    self.tools.append((tool, args))
                    self.log.append(f"   ⚙ {tool}({_short(args, 110)})")
                elif name == "site_directive":
                    directive = e["value"]
                elif name == "sources":   # the source chips under the answer: [{title, section?}]
                    self.sources += list((e.get("value") or {}).get("items") or [])
                elif name == "run_stats":
                    v = e.get("value") or {}
                    for k, n in (v.get("tokens") or {}).items():
                        if k in self.tokens and isinstance(n, (int, float)):
                            self.tokens[k] += n
                    self.stats.append({"ttft_ms": v.get("ttft_ms"), "total_ms": v.get("total_ms"),
                                       "tools": len(v.get("tools") or []),
                                       "tool_errors": sum(1 for t in v.get("tools") or [] if t.get("error")),
                                       "output_tokens": (v.get("tokens") or {}).get("output"), "model_ms": v.get("model_ms")})
                elif name == "ui_directive" and self.form:
                    self.form.directive(e["value"])
                    self.log.append(f"   🔦 highlight {e['value'].get('target')}")
                elif name == "on_interrupt":   # a JSON string (ag-ui-langgraph convention)
                    interrupt = json.loads(e["value"]) if isinstance(e["value"], str) else e["value"]
        except httpx.HTTPError as ex:
            self.errors.append(f"{type(ex).__name__}: {ex}")
            return
        if directive and directive.get("type") == "navigate":
            self.go(directive.get("path") or "/")
            if directive.get("form_id") and directive.get("handoff") != "done" and not interrupt:
                # the page opened the form: the form agent's first run, with the note Dushes kept
                self._run({"threadId": self.thread, "state": self.state(), "forwardedProps": {"handoff": True}}, depth + 1)
                return
        if not interrupt:
            return
        kind = interrupt.get("type") or ("set_fields" if "changes" in interrupt else "card")
        self.cards.append({**interrupt, "type": kind})
        if kind == "ask":
            reply = self.answer(interrupt)
            opts = ", ".join(o.get("label", "") for o in interrupt.get("options") or [])
            self.log.append(f"   ❓ question card: {interrupt.get('question')} [{opts}] → the user answered "
                            f"{json.dumps(reply, ensure_ascii=False) if reply else 'nothing (closed it)'}")
            self._resume({"answer": reply} if reply else {"accepted": False}, depth)
        elif "changes" in interrupt and self.form:
            ch = interrupt["changes"]
            self.log.append("   🃏 card shown and accepted by the user (the form now has these values): "
                            + "; ".join(f"{c.get('label')} = {c.get('display')}" for c in ch))
            self.form.apply({c["name"]: c["value"] for c in ch})
            self._resume({"accepted": True, "config": self.form.config, "ui": self.form.ui}, depth)
        else:   # a confirmation and a review are confirmed (the user means to submit); an upload request or another card is closed
            accepted = kind in ("confirm", "review")
            self.log.append(f"   📋 {kind} card → the user {'confirmed it' if accepted else 'closed it'}")
            reply: dict[str, Any] = {"accepted": accepted}
            if self.form:
                reply.update(config=self.form.config, ui=self.form.ui)
            self._resume(reply, depth)

    def finish(self) -> list[dict]:
        """The conversation as the server keeps it, with who answered each message."""
        r = self.http.get(f"{self.site}/threads/{self.thread}")
        self.messages = r.json().get("messages", []) if r.status_code == 200 else []
        return self.messages

    def transcript(self) -> str:
        return "\n".join(self.log)

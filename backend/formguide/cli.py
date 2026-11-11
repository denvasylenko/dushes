"""The `formguide` command.

    formguide init my-agent                        # starter config, a skill and a domain pack
    formguide check --config my-agent/formguide.yaml   # load it and report, without calling a model
    formguide serve --config my-agent/formguide.yaml --port 8000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STARTER_YAML = """\
# formguide configuration. Paths are relative to this file; ${ENV_VARS} are expanded.
# Only `model` is needed; everything else has a default.

model: "anthropic:claude-opus-5-5"     # any init_chat_model string: "openai:gpt-5", "azure_openai:<deployment>", ...
# models:                              # or one model per role
#   agent: {provider: anthropic, model: claude-opus-5-5, max_tokens: 16000}
#   research: "anthropic:claude-sonnet-5-5"
#   extract: {class: "langchain_openai:AzureChatOpenAI", azure_deployment: gpt-5, api_version: "2025-04-01-preview"}

data_dir: data
domain_packs: {dir: domain_packs}      # <form_id>.json: persona, flow hints, business rules
skills: {dir: skills}                  # <skill>/SKILL.md, optional tools
knowledge:
  dir: data/kb                         # documents managers upload per form (POST /kb/<namespace>/documents)
  index: bm25                          # or {factory: "my_app.vectors:make_store"} for a LangChain vector store
  # scopes: {my_form: [my_form, common]}
checkpointer: {sqlite: data/checkpoints.sqlite}   # model history survives restarts
transcripts: {dir: data/transcripts}              # what the user saw, to restore the chat
interrupt_mode: legacy                 # cards: legacy (CopilotKit) | structured (AG-UI 1.0) | both
"""

STARTER_PACK = {
    "title": "My form",
    "persona": "You help users fill in this form.",
    "flow_hints": ["Fill the steps in order; later steps unlock when earlier ones are complete."],
    "rules": [],
    "glossary": {"some_field_name": "What this field means and where the user finds the value."},
    "pii": [],
}

STARTER_SKILL = """\
---
name: example_skill
description: Example skill. Describe when the agent should use it; the body is loaded on demand.
---
Write the instructions for this situation here: what to ask, which fields to fill, what to check.
"""


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    files = {
        root / "formguide.yaml": STARTER_YAML,
        root / "domain_packs" / "my_form.json": json.dumps(STARTER_PACK, indent=2) + "\n",
        root / "skills" / "example_skill" / "SKILL.md": STARTER_SKILL,
    }
    for path, text in files.items():
        if path.exists() and not args.force:
            print(f"exists, kept: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    print(f"\nNext: formguide check --config {root / 'formguide.yaml'}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    from .config import load_config

    try:
        cfg = load_config(args.config)
    except Exception as e:  # noqa: BLE001
        print(f"config error: {type(e).__name__}: {e}")
        return 1
    m = cfg.models

    def show(spec) -> str:
        return spec if isinstance(spec, str) else json.dumps(spec) if isinstance(spec, dict) else type(spec).__name__

    print(f"config: {Path(args.config).resolve()}")
    print(f"data_dir: {cfg.data_dir}")
    for role in ("agent", "research", "compile", "extract"):
        spec = getattr(m, role)
        print(f"model {role}: {show(spec) if spec else '(same as agent)'}")
    packs = cfg.domain_packs
    names = packs.available() if packs else []
    print(f"domain packs: {', '.join(names) or '(none: neutral persona)'}")
    skills = cfg.skills.all() if cfg.skills else []
    print(f"skills: {', '.join(s.name for s in skills) or '(none)'}")
    if cfg.knowledge:
        print(f"knowledge: {cfg.knowledge.store.root} index={type(cfg.knowledge.index).__name__} "
              f"scopes={cfg.knowledge.scopes or '{}'}")
    print(f"tools: {', '.join(t.name for t in cfg.tools) or '(none)'}")
    print(f"interrupt_mode: {cfg.interrupt_mode}")
    import os

    langsmith = os.environ.get("LANGSMITH_TRACING", os.environ.get("LANGCHAIN_TRACING_V2", "")).lower() == "true"
    hooks = [getattr(f, "__name__", type(f).__name__) for f in cfg.tracing.callbacks]
    print(f"tracing: LangSmith {'on' if langsmith else 'off (set LANGSMITH_TRACING=true and LANGSMITH_API_KEY)'}"
          + (f"; callbacks: {', '.join(hooks)}" if hooks else "") + (f"; tags: {cfg.tracing.tags}" if cfg.tracing.tags else ""))
    print("components:")
    for tag, role in cfg.components.containers.items():
        print(f"  <{tag}> container {role}")
    for tag in cfg.components.fields:
        sp = cfg.components.spec(tag)
        extra = {k: v for k, v in (("value", sp.shape), ("option_keys", sp.option_keys),
                                   ("options_prop", sp.options_prop if sp.options_prop != "options" else None),
                                   ("true", sp.true if sp.true is not True else None),
                                   ("false", sp.false if sp.false is not False else None),
                                   ("format", sp.format if sp.role == "date" else None), ("codec", sp.codec))
                 if v is not None}
        print(f"  <{tag}> {sp.role}" + ("".join(f" {k}={v}" for k, v in extra.items())))
    if args.jsx:
        from .form.layout import LayoutIndex
        from .form.values import value_warnings

        lay = LayoutIndex(Path(args.jsx).read_text(encoding="utf-8"), cfg.components)
        warnings = list(lay.warnings)
        if args.form_config:
            warnings += value_warnings(lay, json.loads(Path(args.form_config).read_text(encoding="utf-8")))
        print(f"form {args.jsx}: {len(lay.nodes)} nodes, {sum(1 for _ in lay.fields())} fields")
        for w in warnings:
            print(f"  warning: {w}")
        if warnings:
            print(f"{len(warnings)} warning(s)")
            return 1
    print("OK")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn

        from .app import create_app
    except ImportError as e:
        print(f"{e}. The server needs: pip install 'formguide[server]'")
        return 1

    app = create_app(args.config, prefix=args.prefix, cors=args.cors or None, static_dir=args.static)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="formguide", description="A chat agent that guides users through forms.")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="write a starter configuration")
    i.add_argument("dir", nargs="?", default=".")
    i.add_argument("--force", action="store_true", help="overwrite existing files")
    c = sub.add_parser("check", help="load a configuration and report it (no model calls)")
    c.add_argument("--jsx", help="also check a form: its JSX file")
    c.add_argument("--form-config", help="with --jsx: a sample config JSON {props, state} to check value formats")
    c.add_argument("--config", default="formguide.yaml")
    s = sub.add_parser("serve", help="run the agent endpoints (needs the `server` extra)")
    s.add_argument("--config", default=None)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--prefix", default="/agent")
    s.add_argument("--cors", action="append", help="allowed origin (repeat); '*' for development")
    s.add_argument("--static", default=None, help="serve a built frontend from this folder")
    args = p.parse_args(argv)
    return {"init": cmd_init, "check": cmd_check, "serve": cmd_serve}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

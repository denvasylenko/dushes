"""One name per thing: fail when the docs use a retired name.

    python3 scripts/check_names.py

The owner's decision of 15.11.2026: the agent for a form or a screen is the "UI agent"; "Dushes" is the package and
the site agent. A retired name in a docs page, a site component, the README or a main spec (`openspec/specs`, which the site
publishes under Specifications and in `llms-full.txt`) fails here with its file and line.
RETIRED lists the names and where each may still appear until its owner changes it (WAITING); the code names
(`FormGuide`, `formguide`, `@formguide/agui-chat`, `formguide.yaml`) join the list in the release that renames the code.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WHERE = [ROOT / "site" / "src", ROOT / "README.md", ROOT / "openspec" / "specs"]
SKIP = ("/reference/specifications/",)   # generated from openspec/specs, which is scanned itself

# (pattern, what to write instead)
RETIRED = [
    (re.compile(r"\bform (?:assistant|agent)\b", re.I), "UI agent"),
]
# files that may still hold a retired name, with who changes them
WAITING: dict[str, str] = {
    # the Tech Lead's behaviour specs say "form agent" throughout; they change with the code rename
    **{f"openspec/specs/{c}/spec.md": "Tech Lead" for c in (
        "dushes", "agent-turn", "agent-context", "chat-history", "agui-protocol", "run-observability")},
}


def main() -> int:
    bad = []
    for base in WHERE:
        files = [base] if base.is_file() else [f for f in base.rglob("*") if f.is_file() and f.suffix in (".md", ".mdx", ".astro", ".ts", ".tsx", ".html", ".json", ".mjs")]
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            if any(s in f"/{rel}" for s in SKIP) or rel in WAITING:
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                for pat, instead in RETIRED:
                    m = pat.search(line)
                    if m:
                        bad.append(f'{rel}:{n} "{m.group(0)}" -> "{instead}"')
    for b in bad:
        print(b)
    print(f"{len(bad)} retired names" + (f"; {len(WAITING)} files wait for their owner" if WAITING else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""Check every internal link of the built docs site: the target page exists and so does the #anchor.

    python3 scripts/check_links.py site/dist            # the base path defaults to /dushes
    python3 scripts/check_links.py site/dist --base /   # a build with DOCS_BASE=/

External links (http, mailto, data) are not fetched. Exits with 1 when a link is broken, so CI fails.
"""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

HREF = re.compile(r'href="([^"]*)"')
ID = re.compile(r'id="([^"]+)"')


def check(dist: Path, base: str) -> tuple[int, list[tuple[str, str, str]]]:
    base = "/" + base.strip("/") + "/" if base.strip("/") else "/"
    ids: dict[Path, set[str]] = {}
    bad: set[tuple[str, str, str]] = set()
    n = 0
    for f in sorted(dist.rglob("*.html")):
        route = base + str(f.relative_to(dist)).replace("index.html", "")
        for href in HREF.findall(f.read_text(encoding="utf-8")):
            if not href or href.startswith(("http:", "https:", "mailto:", "data:", "//")):
                continue
            path, _, frag = href.partition("#")
            n += 1
            if not path:
                target = f
            else:
                url = path if path.startswith("/") else posixpath.normpath(posixpath.join(route, path)) + ("/" if path.endswith("/") else "")
                if not url.startswith(base.rstrip("/") or "/"):
                    bad.add((route, href, "outside the site"))
                    continue
                p = dist / url[len(base):]
                target = p if p.is_file() else p / "index.html"
                if not target.is_file():
                    bad.add((route, href, "no such page"))
                    continue
            if frag and frag != "_top" and target.suffix == ".html":
                if target not in ids:
                    ids[target] = set(ID.findall(target.read_text(encoding="utf-8")))
                if frag not in ids[target]:
                    bad.add((route, href, "no such anchor"))
    return n, sorted(bad)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dist", type=Path)
    ap.add_argument("--base", default="/dushes")
    a = ap.parse_args()
    n, bad = check(a.dist, a.base)
    print(f"{n} links, {len(bad)} broken")
    for page, href, why in bad:
        print(f"  {page}: {href} ({why})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

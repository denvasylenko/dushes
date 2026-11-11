"""Build the GitHub Pages site from the architecture pages + the OpenSpec specs.

    python3 scripts/build_docs_site.py          # writes docs/site/index.html

Source of truth:
- docs/architecture-pages.html  the pages (also published as the claude.ai artifact)
- openspec/specs/*/spec.md      rendered into an extra "Specifications" page at build time
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "docs" / "architecture-pages.html"
SPECS = ROOT / "openspec" / "specs"
OUT = ROOT / "docs" / "site"

# What the artifact viewer adds around a page (charset, viewport, small reset), reproduced for Pages.
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="How formguide works: a chat agent that guides users through large configurable forms.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%230d6e66'/%3E%3Cpath d='M9 10h14M9 16h10M9 22h6' stroke='white' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E">
<style>
:root { color-scheme: light; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
body { margin: 0; font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
img { max-width: 100%; }
[hidden] { display: none !important; }
.spec { border-top: 1px solid var(--line); padding-top: 18px; margin-top: 26px; }
.spec h3 { font: 600 15px var(--f-display); margin: 18px 0 6px; }
.spec h4 { font: 500 13px var(--f-mono); color: var(--muted); margin: 12px 0 4px; letter-spacing: .02em; }
.spec ul { margin: 0 0 8px; padding-left: 18px; }
.spec-index { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 8px; padding: 0; list-style: none; }
.spec-index a { font: 13px var(--f-mono); color: var(--accent); text-decoration: none; border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; background: var(--surface); }
</style>
"""


def inline(md: str) -> str:
    t = html.escape(md, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return t


def render_spec(name: str, text: str) -> str:
    out = [f'<article class="spec" id="spec-{name}">']
    in_list = False
    for line in text.splitlines():
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("# "):
            out.append(f"<h2>{inline(line[2:].replace(' Specification', ''))}</h2>")
        elif line.startswith("## "):
            if line[3:] not in ("Purpose", "Requirements"):
                out.append(f"<h3>{inline(line[3:])}</h3>")
        elif line.startswith("### Requirement: "):
            out.append(f"<h3>{inline(line[len('### Requirement: '):])}</h3>")
        elif line.startswith("#### Scenario: "):
            out.append(f"<h4>Scenario · {inline(line[len('#### Scenario: '):])}</h4>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    out.append("</article>")
    return "\n".join(out)


def specs_section() -> str:
    specs = sorted(p.parent.name for p in SPECS.glob("*/spec.md"))
    index = "".join(f'<li><a href="#specs" data-spec="spec-{n}">{n}</a></li>' for n in specs)
    body = "\n".join(render_spec(n, (SPECS / n / "spec.md").read_text()) for n in specs)
    return f"""
    <section data-page="specs" hidden>
      <p class="eyebrow">Specifications</p>
      <h1>Behaviour contracts, one per capability</h1>
      <p class="lead">Generated from <code>openspec/specs/</code> on every build. Requirements use SHALL; each one has at least one WHEN / THEN scenario. {len(specs)} capabilities.</p>
      <ul class="spec-index">{index}</ul>
      {body}
    </section>
"""


def build() -> Path:
    src = PAGES.read_text()
    cut = src.index("</style>") + len("</style>")
    head_part, body_part = src[:cut], src[cut:]
    nav_end = body_part.index("</ol>")
    body_part = body_part[:nav_end] + '      <li><a href="#specs">Specifications</a></li>\n    ' + body_part[nav_end:]
    pager = body_part.index('<div class="pager">')
    body_part = body_part[:pager] + specs_section() + "\n    " + body_part[pager:]
    # jump to a spec from the index chips
    body_part = body_part.replace("</script>", """
document.addEventListener('click', (e) => {
  const a = e.target.closest('[data-spec]');
  if (a) setTimeout(() => document.getElementById(a.dataset.spec)?.scrollIntoView({ behavior: 'smooth' }), 30);
});
</script>""", 1)
    page = HEAD + head_part + "\n</head>\n<body>\n" + body_part + "\n</body>\n</html>\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page)
    (OUT / ".nojekyll").write_text("")
    return OUT / "index.html"


if __name__ == "__main__":
    print(f"wrote {build().relative_to(ROOT)}")

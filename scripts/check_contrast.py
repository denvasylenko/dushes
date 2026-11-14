#!/usr/bin/env python3
"""Text contrast of the docs site's ink tokens, in both themes, without a browser.

Resolves --fg-ink, --fg-ink-2 and --fg-ink-3 against the surfaces text sits on (the page, a tile or card, a menu)
from Starlight's props.css and site/src/styles/theme.css: var(), hsl()/hsla(), #hex and
color-mix(in srgb, ...). Fails when any pair is under 4.5:1 (WCAG AA for body text).

    python3 scripts/check_contrast.py          # needs site/node_modules (npm ci in site/)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROPS = ROOT / "site/node_modules/@astrojs/starlight/dist/style/props.css"
THEME = ROOT / "site/src/styles/theme.css"
INKS = ["--fg-ink", "--fg-ink-2", "--fg-ink-3"]
SURFACES = {"page": "--sl-color-bg", "tile": "--fg-surface", "menu": "--fg-elevated"}
MIN = 4.5

RGBA = tuple[float, float, float, float]


def blocks(css: str) -> dict[str, dict[str, str]]:
    """Custom properties of the `:root` and `:root[data-theme='light']` rules, at the top level or inside an
    @layer (rules inside @media and other at-rules are skipped)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out: dict[str, dict[str, str]] = {"dark": {}, "light": {}}
    stack: list[str] = []   # the selector or at-rule of each open block
    start = 0
    for i, ch in enumerate(css):
        if ch == "{":
            stack.append(css[start:i].strip())
            start = i + 1
        elif ch == "}":
            sel = stack.pop() if stack else ""
            body = css[start:i]
            outer_ok = all(s.startswith("@layer") for s in stack)
            if outer_ok and not sel.startswith("@"):
                sel = sel.replace('"', "'")
                theme = "light" if "data-theme='light'" in sel else "dark" if sel.split(",")[0].strip() == ":root" else None
                if theme:
                    for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body):
                        out[theme][name] = value.strip()
            start = i + 1
        elif ch == ";" and (not stack or stack[-1].startswith("@")):
            start = i + 1
    return out


def split_args(s: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return parts


def hsl(h: float, s: float, l: float) -> tuple[float, float, float]:
    s, l = s / 100, l / 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return r + m, g + m, b + m


def resolve(value: str, props: dict[str, str]) -> RGBA:
    value = value.strip()
    if value.startswith("var("):
        inner = split_args(value[4:-1])
        return resolve(props.get(inner[0], inner[1] if len(inner) > 1 else "transparent"), props)
    if value == "transparent":
        return (0, 0, 0, 0)
    if value.startswith("#"):
        h = value[1:]
        h = "".join(c * 2 for c in h) if len(h) in (3, 4) else h
        vals = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        return (vals[0], vals[1], vals[2], vals[3] if len(vals) > 3 else 1)
    m = re.match(r"hsla?\((.*)\)$", value)
    if m:
        args = [a.strip() for a in re.split(r"[,\s/]+", m.group(1)) if a.strip()]
        nums = []
        for a in args:
            if a.startswith("var("):
                a = props[a[4:-1].strip()]
            nums.append(float(a.rstrip("%deg")))
        r, g, b = hsl(nums[0], nums[1], nums[2])
        return (r, g, b, nums[3] if len(nums) > 3 else 1)
    m = re.match(r"color-mix\(in srgb,(.*)\)$", value)
    if m:
        (a, pa), (b, pb) = [parse_stop(x) for x in split_args(m.group(1))]
        if pa is None and pb is None:
            pa = pb = 50.0
        pa = 100 - pb if pa is None else pa
        pb = 100 - pa if pb is None else pb
        ca, cb = resolve(a, props), resolve(b, props)
        wa, wb = pa / (pa + pb), pb / (pa + pb)
        alpha = ca[3] * wa + cb[3] * wb
        if alpha == 0:
            return (0, 0, 0, 0)
        rgb = [(ca[i] * ca[3] * wa + cb[i] * cb[3] * wb) / alpha for i in range(3)]
        return (rgb[0], rgb[1], rgb[2], alpha)
    raise ValueError(f"cannot resolve colour: {value}")


def parse_stop(s: str) -> tuple[str, float | None]:
    m = re.match(r"(.*?)\s+([\d.]+)%$", s.strip())
    return (m.group(1), float(m.group(2))) if m else (s.strip(), None)


def over(fg: RGBA, bg: RGBA) -> tuple[float, float, float]:
    return tuple(fg[i] * fg[3] + bg[i] * (1 - fg[3]) for i in range(3))  # type: ignore[return-value]


def luminance(c: tuple[float, float, float]) -> float:
    f = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    x, y = sorted([luminance(a), luminance(b)], reverse=True)
    return (x + 0.05) / (y + 0.05)


def main() -> int:
    if not PROPS.exists():
        print(f"missing {PROPS.relative_to(ROOT)}: run npm ci in site/")
        return 2
    sl, fg = blocks(PROPS.read_text()), blocks(THEME.read_text())
    failed = 0
    for theme in ("dark", "light"):
        props = {**sl["dark"], **(sl["light"] if theme == "light" else {}),
                 **fg["dark"], **(fg["light"] if theme == "light" else {})}
        page = over(resolve(props["--sl-color-bg"], props), (0, 0, 0, 1))
        for ink in INKS:
            row = []
            for name, token in SURFACES.items():
                surface = over(resolve(props[token], props), (*page, 1))
                r = ratio(over(resolve(props[ink], props), (*surface, 1)), surface)
                failed += r < MIN
                row.append(f"{name} {r:.2f}{'  < ' + str(MIN) if r < MIN else ''}")
            print(f"{theme:5} {ink:11} " + " | ".join(row))
    if failed:
        print(f"{failed} pair(s) under {MIN}:1")
        return 1
    print(f"OK: every ink token is at least {MIN}:1 on the page, a tile and a menu, light and dark.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

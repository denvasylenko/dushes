"""Shared helpers for the research corpora generator: a tiny PDF writer, deterministic names, tables, boilerplate.

Everything is fictional: companies, towns, people, phone numbers and laws are invented; no real personal data.
"""
from __future__ import annotations

import random
import textwrap

# ===================================================================== a minimal PDF writer (no dependencies)
# Helvetica with WinAnsiEncoding covers English, German and Spanish (cp1252), which is all the corpora use.

_LINES_PER_PAGE = 62
_WRAP = 100


def _esc(s: str) -> bytes:
    raw = s.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _layout(markdown: str) -> list[list[tuple[str, str]]]:
    """Markdown -> pages of (font, line). Headings become bold lines, tables stay as text rows."""
    lines: list[tuple[str, str]] = []
    for raw in markdown.splitlines():
        if raw.startswith("#"):
            lines.append(("F1", ""))
            lines.append(("F2", raw.lstrip("# ").strip()))
            continue
        if raw.startswith("|"):
            cells = [c.strip() for c in raw.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            raw = "   ".join(cells)
        for part in textwrap.wrap(raw, _WRAP) or [""]:
            lines.append(("F1", part))
    return [lines[i:i + _LINES_PER_PAGE] for i in range(0, len(lines), _LINES_PER_PAGE)] or [[("F1", "")]]


def render_pdf(markdown: str, title: str) -> bytes:
    pages = _layout(markdown)
    objs: list[bytes] = []

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    catalog = add(b"")   # filled in at the end
    pages_id = add(b"")
    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    kids = []
    for n, page in enumerate(pages, 1):
        ops = [b"BT", b"/F1 9 Tf", b"12 TL", b"50 790 Td"]
        for font, text in page:
            ops.append(f"/{font} {10 if font == 'F2' else 9} Tf".encode())
            ops.append(b"(" + _esc(text) + b") Tj T*")
        ops += [b"/F1 8 Tf", b"T*", b"(" + _esc(f"{title} - page {n} of {len(pages)}") + b") Tj", b"ET"]
        stream = b"\n".join(ops)
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                        b"/Contents %d 0 R >>" % (pages_id, f1, f2, content)))
    objs[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id
    objs[pages_id - 1] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids) + b"] /Count %d >>" % len(kids)
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref)
    return bytes(out)


# ===================================================================== deterministic invented names

_SYL = ["al", "der", "bren", "cor", "dal", "en", "fen", "gar", "hol", "is", "kel", "lin", "mar", "nor", "or", "pen",
        "quin", "ros", "sal", "tor", "ul", "ven", "wyn", "yar", "zel", "ash", "brook", "mere", "stead", "wick"]
_FIRST = ["Alex", "Robin", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Jamie", "Avery", "Quinn", "Rowan",
          "Kai", "Noel", "Sasha", "Elia", "Dana", "Milan", "Ari", "Toni"]
_LAST = ["Varnell", "Osterby", "Kettridge", "Lowmoor", "Brannick", "Delacorte", "Fenwright", "Halloway", "Ironsby",
         "Jessop", "Kirwan", "Larkmoor", "Merriden", "Northcott", "Oakhurst", "Pellow", "Quarrie", "Rendle", "Sallow",
         "Tregarth"]


def town(rng: random.Random) -> str:
    return "".join(rng.choice(_SYL) for _ in range(rng.choice([2, 2, 3]))).capitalize()


def towns(rng: random.Random, n: int, exclude: set[str] = frozenset()) -> list[str]:
    out: list[str] = []
    while len(out) < n:
        t = town(rng)
        if t not in out and t not in exclude and 5 <= len(t) <= 12:
            out.append(t)
    return out


def person(rng: random.Random) -> str:
    return f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"


def phone(rng: random.Random, prefix: str = "+00 31") -> str:
    """Invented numbers in the non-existent +00 country code."""
    return f"{prefix} {rng.randint(100, 999)} {rng.randint(1000, 9999)}"


def table(header: list[str], rows: list[list[object]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def eur(x: float, decimals: int = 0) -> str:
    return f"€{x:,.{decimals}f}"


# ===================================================================== boilerplate clauses (volume without facts)
# These paragraphs carry no numbers, prices or deadlines, so they never contradict a gold answer.

_GENERIC = [
    "Headings in this document are for convenience only and do not affect its interpretation. Words in the singular include the plural and the other way round.",
    "Where this document refers to a person, that includes a company, a partnership and any other body with legal personality, and their lawful successors.",
    "Nothing in this document limits any right that cannot be limited under the law that applies to it. If a provision is found invalid, the rest remains in force.",
    "We may rely on information you give us. You must tell us promptly when that information changes, because a change may affect the service or the price.",
    "Notices must be given in writing. A notice sent through the customer portal counts as written notice from the moment it is shown as delivered.",
    "We process personal data as described in our privacy notice. We keep records only for as long as we need them for the purposes stated there.",
    "We may appoint agents and subcontractors to perform any part of this agreement. We remain responsible for what they do on our behalf.",
    "A failure or delay in exercising a right is not a waiver of that right, and a single or partial exercise does not prevent any further exercise of it.",
    "This document and the documents it refers to are the whole agreement between the parties on its subject and replace any earlier understanding.",
    "Any change to this document must be agreed in writing, except where it says that we may change a part of it by publishing a new version.",
    "If there is a conflict between a schedule and the main text, the schedule applies for the matter it covers and the main text applies for everything else.",
    "Each party will act in good faith and will cooperate reasonably with the other to give effect to the purpose of this document.",
    "Staff are trained to explain these terms in plain language. If anything is unclear, ask for an explanation before you rely on your understanding of it.",
    "Copies of earlier versions of this document are kept in the archive and can be requested. They apply only to the period stated on their cover.",
    "Where an amount is stated including tax, the tax rate in force on the date of the invoice applies, and a change in the rate changes the amount accordingly.",
    "References to a law include that law as amended or re-enacted from time to time and any regulation made under it.",
    "The parties will try to resolve any dispute by discussion between senior representatives before starting formal proceedings.",
    "Customers with accessibility needs can ask for this document in large print, audio or another format at no extra cost.",
]


def boilerplate(rng: random.Random, n: int, prefix: str = "General condition") -> str:
    picks = [rng.choice(_GENERIC) for _ in range(n)]
    return "\n\n".join(f"**{prefix} {i}.** {p}" for i, p in enumerate(picks, 1))

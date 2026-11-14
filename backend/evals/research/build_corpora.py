"""Write the Researcher benchmark corpora into demo/research_corpora/<name>/ (deterministic: same output every run).

    cd backend && uv run python evals/research/build_corpora.py          # (re)write all corpora
    cd backend && uv run python evals/research/build_corpora.py --check  # fail if the files on disk differ

All companies, people, places, phone numbers and laws are invented. A "page" in the size report is 3,000 characters of
extracted text (about one printed page).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen import brightline, northwind, quanta  # noqa: E402
from gen.common import render_pdf  # noqa: E402

OUT = HERE.parents[1] / "demo" / "research_corpora"
CORPORA = {"northwind_insurance": northwind, "brightline_freight": brightline, "quanta_cloud": quanta}
PAGE_CHARS = 3000


def files(name: str) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for fname, body in CORPORA[name].build().items():
        if isinstance(body, tuple):   # ("pdf", markdown source, title)
            _, src, title = body
            out[fname] = render_pdf(src, title)
        else:
            out[fname] = body.encode("utf-8")
    return out


def extracted_chars(fname: str, data: bytes) -> int:
    if fname.endswith(".pdf"):
        import io

        from pypdf import PdfReader
        return sum(len(p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    return len(data.decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="compare with the files on disk instead of writing")
    a = ap.parse_args()
    total = 0
    bad = []
    for name in CORPORA:
        d = OUT / name
        fs = files(name)
        chars = 0
        for fname, data in fs.items():
            p = d / fname
            if a.check:
                if not p.exists() or p.read_bytes() != data:
                    bad.append(str(p))
            else:
                d.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            chars += extracted_chars(fname, data)
        if not a.check:
            for stale in d.iterdir():
                if stale.name not in fs:
                    stale.unlink()
        pages = chars / PAGE_CHARS
        total += pages
        print(f"{name:<22} {len(fs):>2} documents  {chars:>8,} chars  ~{pages:5.1f} pages")
    print(f"{'total':<22}              ~{total:5.1f} pages")
    if bad:
        print("out of date (run build_corpora.py):\n  " + "\n  ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

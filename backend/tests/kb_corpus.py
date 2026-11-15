"""Generated large documents with planted facts, for the retrieval tests (no model, the same text every run)."""
from __future__ import annotations

import random

PAGE_CHARS = 2400   # about one printed page

WORDS = ("the applicant must provide a copy of each document before the office reviews request and fee cost month "
         "payment period service customer account contract terms notice change apply during after within working "
         "days written form section table rate amount total limit minimum maximum annual general rules conditions "
         "department manager approval record report standard additional required available following including "
         "information system process access level type date number name address status order item value").split()

TOPICS = ("parking permits", "late payment", "equipment rental", "guest access", "data retention", "travel expenses",
          "overtime work", "refund requests", "key cards", "night shifts", "storage lockers", "training courses",
          "sick leave", "delivery slots", "membership upgrades", "visitor badges", "printing quotas", "room bookings",
          "warranty claims", "safety inspections", "language classes", "tool calibration", "waste disposal",
          "shuttle buses", "uniform orders", "locker deposits", "exam retakes", "archive requests", "pet policy",
          "bicycle storage")


def _filler(rng: random.Random, chars: int) -> str:
    out, size = [], 0
    while size < chars:
        sentence = " ".join(rng.choice(WORDS) for _ in range(rng.randint(8, 18))).capitalize() + "."
        out.append(sentence)
        size += len(sentence) + 1
    return " ".join(out)


def handbook(name: str, pages: int, seed: int, topics: tuple[str, ...] = TOPICS, pdf: bool = False) -> tuple[str, list[dict]]:
    """(text, facts): a document of about `pages` pages in chapters and numbered sections, with one planted fact
    per topic: {topic, figure, heading, sentence, name}. `pdf`: page breaks and bare numbered headings, as
    extracted from a PDF; otherwise markdown headings."""
    rng = random.Random(seed)
    chapters = max(4, pages // 12)
    per_chapter = max(3, (pages * PAGE_CHARS) // (chapters * 2200))
    slots = [(c, s) for c in range(1, chapters + 1) for s in range(1, per_chapter + 1)]
    planted = dict(zip(rng.sample(slots, len(topics)), topics))
    lines, facts, size, page = [], [], 0, 1
    if pdf:
        lines.append("## Page 1")
    for c in range(1, chapters + 1):
        chapter = f"{c} {rng.choice(WORDS).capitalize()} {rng.choice(WORDS)} {name}"
        lines += [chapter if pdf else f"## {chapter}", ""]
        for s in range(1, per_chapter + 1):
            topic = planted.get((c, s))
            heading = f"{c}.{s} {topic.capitalize() if topic else rng.choice(WORDS).capitalize() + ' ' + rng.choice(WORDS)}"
            lines += [heading if pdf else f"### {heading}", ""]
            body = _filler(rng, rng.randint(1600, 2800))
            if topic:
                figure = f"{rng.randint(11, 97)},{rng.randint(10, 99)}"
                sentence = f"For {topic} in {name} the charge is {figure} EUR per month."
                cut = body.find(". ", len(body) // 2) + 2
                body = body[:cut] + sentence + " " + body[cut:]
                facts.append({"topic": topic, "figure": figure, "heading": heading, "sentence": sentence, "name": name})
            para = ""
            for sentence in body.replace(". ", ".\n").split("\n") + [""]:   # paragraphs of whole sentences
                if sentence and len(para) + len(sentence) < 700:
                    para += sentence + " "
                    continue
                if not para.strip():
                    para = sentence + " "
                    continue
                lines += [para.strip(), ""]
                size += len(para)
                para = sentence + " " if sentence else ""
                if pdf and size // PAGE_CHARS + 1 > page:
                    page = size // PAGE_CHARS + 1
                    lines.append(f"## Page {page}")
    return f"# {name}\n\n" + "\n".join(lines), facts

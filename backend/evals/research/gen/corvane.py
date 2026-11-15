"""Control corpus "corvane_university": the regulations of Corvane University (invented), about 65 pages.

It exists for one purpose: the retrieval control (evals/research_depth/control). Nobody tunes retrieval on it and it
is not offered on any demo, so its number says whether a change helps on documents nobody has looked at.
Shapes on purpose: long tables (a course catalogue, a fee schedule by programme, a room list), numbered regulations,
an archived fee schedule next to the current one, a German annex, a PDF.
"""
from __future__ import annotations

import random

from .common import boilerplate, eur, person, phone, table, towns

SEED = 8521
F = {
    "pass_mark": 50, "resits": 2, "resit_cap": 50, "appeal_days": 15, "late_penalty_pct": 5, "late_max_days": 7,
    "credits_year": 60, "credits_bachelor": 180, "credits_master": 120, "max_years_bachelor": 5, "thesis_words": 12000, "thesis_extension_weeks": 4,
    "attendance_pct": 75, "plagiarism_first": "a mark of zero for the piece of work", "tuition_bachelor_2026": 2900, "tuition_bachelor_2025": 2750,
    "tuition_master_2026": 4300, "instalments": 3, "late_fee": 60, "refund_full_days": 14, "refund_half_until": "31 October",
    "scholarship_merit": 1500, "scholarship_gpa": 85, "housing_single": 410, "housing_shared": 290, "housing_deposit": 500, "housing_notice_weeks": 6,
    "library_loans": 15, "library_weeks": 4, "library_fine": 0.3, "exam_registration_days": 10, "exchange_min_credits": 60,
    "de_fee": 185, "de_weeks": 6,
}
FACULTIES = ["Engineering", "Economics", "Law", "Medicine", "Humanities", "Natural Sciences", "Education", "Design"]


def _rng(k: int) -> random.Random:
    return random.Random(SEED + k)


def regulations() -> str:
    return f"""# Corvane University Academic Regulations 2026

In force from 1 September 2026 for all bachelor's and master's programmes. A faculty annex may add rules; it may not lower a requirement of these regulations.

## 1 Credits and duration

1.1 An academic year carries {F['credits_year']} credits. A bachelor's degree needs {F['credits_bachelor']} credits, a master's degree {F['credits_master']}.

1.2 A bachelor's programme must be completed within {F['max_years_bachelor']} years of first enrolment, periods of approved leave not counted.

## 2 Attendance

2.1 Attendance of at least {F['attendance_pct']}% is required in seminars, laboratories and clinical placements. Lectures are not counted.

2.2 A student below that share may not sit the course's examination in that session.

## 3 Examinations

3.1 Students register for each examination at least {F['exam_registration_days']} days before it. A late registration is not accepted.

3.2 The pass mark is {F['pass_mark']} out of 100.

3.3 A failed examination may be resat {F['resits']} times. A resit mark is capped at {F['resit_cap']}, unless the first attempt was missed for a documented reason.

3.4 Results are published within 20 working days of the examination.

## 4 Coursework

4.1 Coursework handed in late loses {F['late_penalty_pct']} marks for each calendar day, up to {F['late_max_days']} days; after that it is not marked.

4.2 An extension is granted by the course leader before the deadline, for illness or another serious reason shown by a document.

## 5 Thesis

5.1 A bachelor's thesis has at most {F['thesis_words']:,} words, excluding references and appendices.

5.2 One extension of up to {F['thesis_extension_weeks']} weeks may be granted by the dean.

## 6 Academic integrity

6.1 Plagiarism, collusion and the use of undeclared AI tools in assessed work are breaches.

6.2 A first breach brings {F['plagiarism_first']} and a recorded warning. A second breach goes to the disciplinary board, which may suspend the student for up to two semesters.

## 7 Appeals

7.1 A student may appeal against a mark within {F['appeal_days']} working days of its publication, in writing, to the faculty examinations office.

7.2 An appeal is about procedure or a clear error; academic judgement itself is not reviewed.

## 8 Leave and withdrawal

8.1 Leave of absence is granted for up to two semesters in a programme.

8.2 A student who withdraws tells the registry in writing; fees are refunded as the Fee Schedule says.

## 9 Exchange

9.1 A student may go on exchange after earning at least {F['exchange_min_credits']} credits. Credits earned abroad are recognised when the learning agreement was signed before departure.

{boilerplate(_rng(1), 14, "Regulation note")}
"""


def fees(year: int) -> str:
    y26 = year == 2026
    rng = _rng(year)
    rows = []
    for f in FACULTIES:
        for lvl in ("Bachelor", "Master"):
            base = (F["tuition_bachelor_2026"] if lvl == "Bachelor" else F["tuition_master_2026"]) if y26 else (F["tuition_bachelor_2025"] if lvl == "Bachelor" else 4100)
            extra = rng.choice([0, 0, 150, 300, 600]) if f in ("Medicine", "Design", "Engineering") else 0
            rows.append([f"{lvl} in {f}", eur(base + extra), eur(extra) if extra else "-", eur(rng.choice([40, 60, 90]))])
    head = ("# Fee Schedule 2026/27\n\nFees for the academic year 2026/27, per year. This schedule replaces the Fee Schedule 2025/26."
            if y26 else "# Fee Schedule 2025/26 (archived)\n\nFees for the academic year 2025/26. Replaced by the Fee Schedule 2026/27 and kept for refunds and disputes about that year.")
    return f"""{head}

## Tuition by programme

{table(["Programme", "Tuition a year", "Of which laboratory or studio fee", "Student union fee"], rows)}

## Paying

Tuition may be paid in {F['instalments']} instalments, due on 15 September, 15 January and 15 April. A payment that is late by more than 10 days carries a late fee of {eur(F['late_fee'] if y26 else 50)}.

## Refunds

A student who withdraws within {F['refund_full_days']} days of the start of the year gets the tuition back in full. A withdrawal until {F['refund_half_until']} gets half. After that nothing is refunded.

## Scholarships

A merit scholarship of {eur(F['scholarship_merit'])} a year goes to students whose average mark in the previous year was at least {F['scholarship_gpa']}. Applications close on 30 June.

{boilerplate(rng, 6, "Fee note")}
"""


def courses() -> str:
    rng = _rng(3)
    subjects = ["Statistics", "Thermodynamics", "Contract Law", "Anatomy", "Microeconomics", "Linear Algebra", "Ethics", "Organic Chemistry", "Pedagogy", "Typography",
                "Programming", "Constitutional Law", "Physiology", "Econometrics", "Materials", "Philosophy of Science", "Genetics", "Didactics", "Product Design", "Signals and Systems"]
    rows = []
    n = 0
    for f in FACULTIES:
        for _ in range(150):
            n += 1
            rows.append([f"{f[:3].upper()}{rng.randint(100, 599)}-{n:03d}", f"{rng.choice(subjects)} {rng.choice(['I', 'II', 'III', 'for ' + f, 'Seminar', 'Laboratory', 'Project'])}", f, rng.choice([3, 5, 5, 6, 7.5, 10]),
                         rng.choice(["autumn", "spring", "both"]), rng.choice(["written examination", "oral examination", "coursework", "project and presentation", "written examination and laboratory report"]),
                         person(rng)])
    return f"""# Course Catalogue 2026/27

Every course offered in 2026/27: its code, credits, semester, how it is assessed and who leads it.

{table(["Code", "Course", "Faculty", "Credits", "Semester", "Assessment", "Course leader"], rows)}
"""


def housing() -> str:
    rng = _rng(4)
    halls = towns(rng, 9)
    rooms = [[h + " Hall", rng.choice(["single", "single", "shared"]), rng.randint(60, 420), rng.choice(["yes", "no"]), rng.choice(["5 min", "10 min", "20 min by tram", "on campus"]), phone(rng)] for h in halls]
    return f"""# Student Housing Rules 2026

## Rents

A single room costs {eur(F['housing_single'])} a month and a place in a shared room {eur(F['housing_shared'])}, heating and internet included. A deposit of {eur(F['housing_deposit'])} is paid with the first rent and returned within 30 days of moving out, less any damage.

## Contracts

A housing contract runs for the academic year. It can be ended early with {F['housing_notice_weeks']} weeks' notice to the end of a month.

## Halls

{table(["Hall", "Rooms", "Places", "Accessible rooms", "To campus", "Office"], rooms)}

## House rules

Quiet hours are from 22:00 to 07:00. Guests may stay up to three nights in a month. Smoking is not allowed in any building.

{boilerplate(rng, 8, "Housing note")}
"""


def library() -> str:
    return f"""# Library Rules

A student may have {F['library_loans']} items on loan at a time, each for {F['library_weeks']} weeks, renewable twice unless someone has reserved the item. An overdue item costs {eur(F['library_fine'], 2)} a day. The reading rooms are open from 08:00 to 23:00 on weekdays and from 10:00 to 20:00 at weekends; during examination weeks they stay open until 02:00.

Group study rooms are booked online, up to 3 hours a day for a group. Interlibrary loans take about 10 working days and are free for thesis work.

{boilerplate(_rng(5), 6, "Library note")}
"""


def annex_de() -> str:
    return f"""# Anhang: Anerkennung ausländischer Abschlüsse

Für Bewerberinnen und Bewerber mit einem Schulabschluss außerhalb von Verdania.

Die Anerkennung wird beim Zulassungsamt beantragt. Die Gebühr beträgt {F['de_fee']} Euro. Die Bearbeitung dauert in der Regel {F['de_weeks']} Wochen. Einzureichen sind beglaubigte Kopien der Zeugnisse und eine beglaubigte Übersetzung, sofern die Zeugnisse nicht auf Deutsch oder Englisch ausgestellt sind.

Ein Sprachnachweis auf dem Niveau B2 ist für alle Studiengänge erforderlich, die auf Englisch unterrichtet werden.
"""


def calendar() -> str:
    rows = [["Enrolment", "1 to 12 September 2026"], ["Autumn semester lectures", "14 September to 18 December 2026"], ["Autumn examinations", "11 to 29 January 2027"],
            ["Spring semester lectures", "8 February to 21 May 2027"], ["Spring examinations", "31 May to 18 June 2027"], ["Resit examinations", "23 August to 3 September 2027"],
            ["Thesis deadline, bachelor", "7 June 2027"], ["Graduation ceremony", "9 July 2027"]]
    return f"""# Academic Calendar 2026/27

{table(["What", "When"], rows)}

No teaching on public holidays of Verdania and on the university day, 4 November.
"""


def faculty_annex(i: int, fac: str) -> str:
    rng = _rng(100 + i)
    labs = [[f"{fac[:2].upper()}-{rng.randint(100, 499)}", rng.choice(["laboratory", "seminar room", "lecture hall", "studio", "computer room", "clinic room", "workshop"]), rng.randrange(12, 240, 4),
             rng.choice(["projector", "projector and recording", "none", "fume hoods", "workstations", "simulation dummies"]), rng.choice(["badge", "badge and induction", "open"])] for _ in range(70)]
    staff = [[rng.choice(["Dean", "Vice-dean for teaching", "Examinations officer", "Exchange coordinator", "Student adviser", "Laboratory manager", "Placement officer"]), person(rng), phone(rng),
              f"{rng.choice(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])} {rng.randint(9, 15)}:00-{rng.randint(16, 18)}:00"] for _ in range(14)]
    return f"""# Faculty Annex: {fac}

Rules of the Faculty of {fac} that add to the Academic Regulations 2026.

## Admission

The faculty admits {rng.randrange(60, 420, 10)} first-year students a year. The entrance examination is held on {rng.randint(1, 28)} June; the pass mark is {rng.choice([55, 60, 65, 70])} out of 100. Applications close on {rng.randint(1, 30)} April.

## Placements and laboratories

A placement of {rng.choice([4, 6, 8, 12, 16])} weeks is required in year {rng.choice([2, 3])}. Laboratory groups have at most {rng.choice([10, 12, 16, 20])} students. A missed laboratory session is made up within {rng.choice([7, 10, 14])} days or the course is failed.

## Thesis

The thesis is supervised by a member of the faculty and defended before a board of {rng.choice([3, 4, 5])}. The defence lasts {rng.choice([20, 30, 45])} minutes. The faculty's own word limit for a master's thesis is {rng.randrange(15000, 32000, 1000):,} words.

## People

{table(["Role", "Name", "Phone", "Office hours"], staff)}

## Rooms

{table(["Room", "Kind", "Seats", "Equipment", "Access"], labs)}

{boilerplate(rng, 10, "Faculty note")}
"""


def build() -> dict[str, bytes | str]:
    return {
        "academic_regulations_2026.pdf": ("pdf", regulations(), "Corvane University Academic Regulations 2026"),
        "fee_schedule_2026_27.md": fees(2026),
        "fee_schedule_2025_26_archived.md": fees(2025),
        "course_catalogue_2026_27.md": courses(),
        "student_housing_rules.md": housing(),
        "library_rules.md": library(),
        "anhang_anerkennung_de.md": annex_de(),
        "academic_calendar_2026_27.md": calendar(),
        **{f"faculty_annex_{f.lower().replace(' ', '_')}.md": faculty_annex(i, f) for i, f in enumerate(FACULTIES)},
    }

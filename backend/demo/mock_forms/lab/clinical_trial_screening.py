"""Lab form: pre-screening for a fictional asthma study (medium; a computed eligibility, sensitive health data).

Rules: the pregnancy question is asked only of female volunteers; the diagnosis date appears when asthma was
diagnosed; the read-only "Eligibility" field says "Likely eligible" or "Not eligible: <reason>" from the criteria
(age 18 to 65, asthma diagnosed 1 year ago or more, not a current smoker, not pregnant, no biologic medicine);
it stays empty until the screening questions are answered; contact consent is required. Not being eligible is not
a form error: the form can still be sent.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "clinical_trial_screening"

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_screening", "1. Screening questions",
      C("Accordion", "acc_about", "About you",
        "This questionnaire only checks whether you might fit the study. It is not medical advice: do not change "
        "any treatment because of it.",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("RadioGroup", "sex", "Sex at birth", required=True, options=opts("female:Female", "male:Male"))),
      C("Accordion", "acc_health", "Asthma and health",
        F("RadioGroup", "asthma_diagnosed", "Has a doctor diagnosed you with asthma?", required=True,
          options=opts("yes:Yes", "no:No")),
        F("DatePicker", "diagnosis_date", "When was it diagnosed? (approximate date)", required=True),
        F("RadioGroup", "smoking", "Do you smoke or vape?", required=True,
          options=opts("never:Never", "former:I used to, but stopped", "current:Yes, currently")),
        F("RadioGroup", "pregnant", "Are you pregnant or breastfeeding?", required=True, options=opts("yes:Yes", "no:No")),
        F("MultiSelect", "medications", "Asthma medicines you use now", required=True,
          options=opts("reliever:Reliever inhaler (blue)", "ics:Preventer inhaler (steroid)",
                       "combo:Combination inhaler", "tablets:Leukotriene tablets", "oral_steroids:Steroid tablets",
                       "biologic:Biologic injection", "none:None")),
        F("Input", "eligibility", "Eligibility (calculated)", readonly=True))),
    C("Tab", "tab_contact", "2. Contact",
      C("Accordion", "acc_contact", "How the study team can reach you",
        F("Input", "phone", "Phone", required=True),
        F("Input", "email", "Email"),
        F("RadioGroup", "contact_method", "Preferred contact", required=True,
          options=opts("phone:Phone call", "email:Email")),
        F("Dropdown", "contact_time", "Best time to call",
          options=opts("morning:Morning", "afternoon:Afternoon", "evening:Evening")),
        F("Checkbox", "contact_consent", "I agree that the study team contacts me about this study", required=True),
        F("Checkbox", "data_consent", "I agree that my answers are stored for this screening only", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Asthma study pre-screening",
    "starters": ["Can I join the asthma study?", "I use a biologic injection, can I take part?", "Is the study paid?"],
    "persona": "You are the pre-screening assistant of the AIRWAY-7 study at Kestrel Research Unit. Be neutral and kind. "
               "Never give medical advice and never suggest changing a treatment; for health questions refer to the "
               "volunteer's own doctor.",
    "flow_hints": [
        "Answer the screening questions first; the Eligibility field is calculated from them.",
        "The pregnancy question is asked only of female volunteers.",
        "If the result is Not eligible, say so plainly with the reason; the form can still be sent.",
        "Contact consent is required to send the form.",
    ],
    "glossary": {
        "eligibility": "Likely eligible: aged 18 to 65, asthma diagnosed at least 1 year ago, not a current smoker, "
                       "not pregnant or breastfeeding, no biologic injection. The study team confirms at a visit.",
        "medications": "Volunteers on a biologic injection cannot join this study.",
        "smoking": "Current smokers and vapers are excluded; former smokers can take part.",
    },
    "pii": ["first_name", "last_name", "birth_date", "phone", "email", "pregnant", "medications", "diagnosis_date"],
}

PAGE = {
    "path": "/lab/asthma-study",
    "title": "AIRWAY-7 asthma study: pre-screening",
    "description": "Pre-screening questionnaire of the AIRWAY-7 asthma study run by Kestrel Research Unit (fictional).",
    "keywords": ["clinical trial", "study", "asthma", "volunteer", "research", "inhaler"],
    "sections": [
        {"id": "who", "title": "Who can take part",
         "text": "Adults aged 18 to 65 with asthma diagnosed at least 1 year ago. Current smokers or vapers, pregnant or "
                 "breastfeeding volunteers and people using a biologic injection cannot take part."},
        {"id": "visits", "title": "What happens next",
         "text": "The study team calls eligible volunteers within 10 working days. Six visits over 12 weeks; travel costs "
                 "are refunded up to 40 EUR per visit. This page is not medical advice."},
    ],
}


def rules(h) -> None:
    age = h.age("birth_date")
    h.a_date("birth_date", past=True)
    female = h.id("sex") == "female"
    h.show("pregnant", when=female)
    h.require("pregnant", when=female)
    asthma = h.id("asthma_diagnosed") == "yes"
    h.show("diagnosis_date", when=asthma)
    h.require("diagnosis_date", when=asthma)
    h.a_date("diagnosis_date", past=True)
    meds = h.ids("medications")
    if "none" in meds and len(meds) > 1:
        h.error("medications", "'None' cannot be combined with a medicine")
    h.phone("phone")
    h.email("email")
    h.require("email", when=h.id("contact_method") == "email")

    years = h.age("diagnosis_date")
    answered = (age is not None and not h.has_error("birth_date") and h.id("asthma_diagnosed") in ("yes", "no")
                and (not asthma or (years is not None and not h.has_error("diagnosis_date")))
                and h.id("smoking") in ("never", "former", "current")
                and (not female or h.id("pregnant") in ("yes", "no")) and bool(meds))
    if not answered:
        return
    if not 18 <= age <= 65:
        reason = "age outside 18 to 65"
    elif not asthma:
        reason = "no asthma diagnosis"
    elif years < 1:
        reason = "asthma diagnosed less than 1 year ago"
    elif h.id("smoking") == "current":
        reason = "current smoker"
    elif female and h.id("pregnant") == "yes":
        reason = "pregnant or breastfeeding"
    elif "biologic" in meds:
        reason = "uses a biologic injection"
    else:
        reason = ""
    h.set("eligibility", f"Not eligible: {reason}" if reason else "Likely eligible")

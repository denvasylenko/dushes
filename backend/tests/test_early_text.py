"""The words start early (a second sentence, or 160 chars), and a lead written before tools is taken back when the
model writes its answer again after them, on the page (CUSTOM text_retract) and in the transcript."""
from formguide.agent.graph import flows

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN

LEAD = "Sure, I can help with that. Let me look at the form first."
ANSWER = "The form has a Loan tab with the amount and the term; the rest is your contact details."


def texts(ev):
    out: dict[str, str] = {}
    for e in ev:
        if e["type"] == "TEXT_MESSAGE_CONTENT":
            out[e["messageId"]] = out.get(e["messageId"], "") + e["delta"]
    return out


def retracted(ev):
    return [e["value"]["messageId"] for e in ev if e["type"] == "CUSTOM" and e.get("name") == "text_retract"]


def test_text_flows_once_a_second_sentence_starts():
    assert not flows("Let me check.")                                   # one short line: held
    assert not flows("Let me look at the form fields for you now")      # one sentence, under 160
    assert flows("Sure, I can help with that today. Let me look")           # a second sentence started
    assert flows("x" * 160)


def test_a_lead_before_tools_is_taken_back_when_the_answer_comes_after(guide, model):
    model.script = [say(LEAD, ("o1", "get_outline", {})), say(ANSWER)]
    ev = collect(guide, "t-lead", message="what is in the form?", state=start(guide, LOAN))
    said = texts(ev)
    lead_id = next(k for k, v in said.items() if v == LEAD)              # shown early, before the tool ran
    assert retracted(ev) == [lead_id]
    names = [e.get("name") or e["type"] for e in ev]
    assert names.index("text_retract") < next(i for i, e in enumerate(ev) if e["type"] == "TEXT_MESSAGE_CONTENT" and e["delta"] == ANSWER)
    shown = [m["content"] for m in guide.thread_messages("t-lead") if m["role"] == "assistant" and m.get("content")]
    assert shown == [ANSWER]                                             # a reload shows the answer only


def test_a_card_lead_and_a_long_text_stay(guide, model):
    model.script = [say(LEAD, ("q1", "ask_user", {"question": "Which loan?", "options": ["Car", "Home"]}))]
    ev = collect(guide, "t-card", message="help me", state=start(guide, LOAN))
    assert LEAD in texts(ev).values() and not retracted(ev)             # a card's sentence is for the user

    long = "Here is what I found in your documents. " * 8
    model.script = [say(long, ("o1", "get_outline", {})), say(ANSWER)]
    ev = collect(guide, "t-long", message="go", state=start(guide, LOAN))
    assert not retracted(ev)                                             # a real reply before tools is never taken back

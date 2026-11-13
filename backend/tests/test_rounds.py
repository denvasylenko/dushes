"""Tool rounds: a chain of card answers is not cut by max_tool_rounds, and the limit ends with a reply."""
from langchain_core.messages import ToolMessage

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value


def ask(i):
    return say("", (f"q{i}", "ask_user", {"question": f"Question {i}?", "options": ["Yes", "No"]}))


def test_card_answers_start_the_rounds_again(guide, model):
    guide.max_tool_rounds = 2
    model.script = [say("", ("o1", "get_outline", {})), ask(1)]
    v = interrupt_value(collect(guide, "t1", message="go", state=start(guide, LOAN)))
    assert v["question"] == "Question 1?"
    for i in (2, 3, 4):   # each answer is new input: the chain goes on past the limit of 2
        model.script = [say("", (f"o{i}", "get_outline", {})), ask(i)]
        v = interrupt_value(collect(guide, "t1", resume={"answer": {"ids": ["Yes"]}}))
        assert v and v["question"] == f"Question {i}?"


def test_the_limit_ends_with_a_reply(guide, model):
    guide.max_tool_rounds = 1
    model.script = [say("", ("o1", "get_outline", {})), say("", ("o2", "get_outline", {})),
                    say("I looked at the form; next I will open the Loan tab.")]
    ev = collect(guide, "t2", message="go", state=start(guide, LOAN))
    text = "".join(e.get("delta", "") for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert "next I will open the Loan tab" in text
    last = model.calls[-1]
    assert any(isinstance(m, ToolMessage) and m.tool_call_id == "o2" and "step limit" in m.content for m in last)
    assert "reached its step limit" in last[-1].content
    assert ev[-1]["type"] == "RUN_FINISHED"
